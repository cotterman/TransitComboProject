################################################################################
###################### The Transit Combo Project  ##############################
################################################################################

import sys
import urllib2
from collections import OrderedDict
from collections import namedtuple
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import matplotlib as mpl
print "Version of matplotlib: " , mpl.__version__   #1.4.3
from mpl_toolkits.basemap import Basemap 
import matplotlib.pyplot as plt

import googlemaps #to biking directions and address to lng/at conversion
sys.path.append('../pygmaps-0.1.1')
import pygmaps #for mapping visual

Trip = namedtuple("Trip", ["start_lat", "start_lng", "end_lat", "end_lng"])
Stop = namedtuple("Stop", ["title", "lat", "lng", "tag"])
Route = namedtuple("Route", ["title","start","end","distance_active"])


#create awesome_merge function for pandas

#create awesome_summary funciton for pandas


def map_data_old(fname, route, path=None):
    
    #min and max values of route (starting and ending locations)
    lng0, lng1, lat0, lat1 = [
        min(route.start_lng, route.end_lng) - 0.05, 
        max(route.start_lng, route.end_lng) + 0.05, 
        min(route.start_lat, route.end_lat) - 0.05, 
        max(route.start_lat, route.end_lat) + 0.05 
    ]
    
    print "boundaries: ", lng0, lng1, lat0, lat1
    f2, ax2 = plt.subplots(figsize=(10,6))

    # Make the map object, where we draw geographic information
    m = Basemap(lng0, lat0, lng1, lat1, resolution='h', ax=ax2)
    m.drawcoastlines()

    # draw parallels.
    parallels = np.arange(lat0,lat1,abs(lat1-lat0)/15.0)
    m.drawparallels(parallels, labels=[1,0,0,0], fontsize=8)
    # draw meridians
    meridians = np.arange(lng0, lng1, abs(lng1-lng0)/15.0)
    m.drawmeridians(meridians, labels=[0,0,0,1], fontsize=8, rotation=25)

    # Scatter plot of start and end locations (desired route with labels) 
    start = m.scatter(route.start_lng, route.start_lat, 
                       s=5, color='forestgreen', alpha=.5)
    end = m.scatter(route.end_lng, route.end_lat,  
                     s=5, color='darkorchid', alpha=.5)
    plt.text(route.start_lng, route.start_lat, "start", color='green', fontsize=10)
    plt.text(route.end_lng, route.end_lat, "end", color='red', fontsize=10)

    plt.title('Route',fontsize=16)
    plt.savefig('../'+fname)


def get_routes(agency_tag):
    """Returns object containing tag and title of routes."""

    agency_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeList&a=" + 
             agency_tag)
    result = urllib2.urlopen(agency_page).read()
    agency_root = ET.fromstring(result)
    routes = {}
    #agency root contains 84 routes as children. i.e., len(agency_root)=84
    for route in agency_root:
        rtag = route.get('tag')
        rtitle = route.get('title')
        routes[rtag] = rtitle
    return routes


def get_directed_routes(agency_tag):
    """Returns object containing tag and title of directed routes."""

    agency_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeList&a=" + 
             agency_tag)
    result = urllib2.urlopen(agency_page).read()
    agency_root = ET.fromstring(result)
    droutes = {}
    for route in agency_root:
        rtag = route.get('tag')
        rtitle = route.get('title')
        route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
                      agency_tag + "&r=" + rtag)
        result = urllib2.urlopen(route_page).read()
        route_root = ET.fromstring(result)  
        assert len(route_root)==1
        route = route_root[0] #get to the child, which has all the route info 
        for ele in route:
            if ele.tag == 'direction':
                rdirections = []
                dtag = ele.attrib['tag']
                dtitle = ele.attrib['title']
                droutes[(rtag,dtag)] = [rtitle, dtitle]
    return droutes


def get_stop_info(agency_tag, routes):
    """Build map from route_tag/stop_tag to stop info (title and location)."""

    #for each route, obtain pickup/dropoff locations
    all_stops_info = {}
    for route_tag in routes:
        route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
                      agency_tag + "&r=" + route_tag)
        result = urllib2.urlopen(route_page).read()
        route_root = ET.fromstring(result)
        #route_root has only one child.  
        assert len(route_root)==1
        route = route_root[0] #get to the child, which has all the route info.
        stops_info = {} 
        #notes on iterators:
            #iter(route) will just iterate of direct children (not grandchildren).
            #route.iter() iterates over all descendants in order of doc appearance.
            #for loop default is to use iter(route), giving direct children only
        for stop in route:
            if stop.tag == 'stop':
                stop_info = Stop(stop.attrib['title'], 
                            float(stop.attrib['lat']), 
                            float(stop.attrib['lon']),
                            stop.attrib['tag'])
                stop_tag = stop.attrib['tag']
                all_stops_info[(route_tag, stop_tag)] = stop_info

    return all_stops_info


def get_droute_info(agency_tag, route_tags, stops_info):
    directed_route_info = OrderedDict()
    for route_tag in route_tags:
        route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
                  agency_tag + "&r=" + route_tag)
        result = urllib2.urlopen(route_page).read()
        route_root = ET.fromstring(result)
        #route_root has only one child.  
        assert len(route_root)==1
        route = route_root[0] #get to the child, which has all the route info 
        for ele in route:
            if ele.tag == 'direction':
                direction_tag = ele.attrib['tag']
                loc_list = []
                for stop in ele:
                    stop_tag = stop.attrib['tag']
                    stop_info = stops_info[route_tag, stop_tag]
                    loc_list.append(stop_info)                        
                directed_route_info[(route_tag, direction_tag)] = loc_list

    return directed_route_info
    

def get_distance((lat0, lng0), (lat1, lng1)):
    """Calculate the manhattan distance between 2 points."""
    alpha = 84.2
    beta = 111.2
    distance = alpha*abs(lng1-lng0) + beta*abs(lat1-lat0)
    return distance


def find_closest_stops(desired_trip, routes_info, routes):
    """For each route, find closest stops to desired trip."""
    route_stop_ratings = OrderedDict()
    min_dist_start = 0
    min_dist_end = 0
    for route in routes_info:
        for stop_i, stop in enumerate(routes_info[route]):
            #get distance from stop location to start and end locations
            dist_start = get_distance(
                (desired_trip.start_lat, desired_trip.start_lng),
                (stop.lat, stop.lng))
            dist_end = get_distance(
                (desired_trip.end_lat, desired_trip.end_lng),
                (stop.lat, stop.lng))
            if stop_i==0 or (dist_start < min_dist_start):
                closest_stop_to_start = stop
                min_dist_start = dist_start
            if stop_i==0 or (dist_end < min_dist_end):
                closest_stop_to_end = stop
                min_dist_end = dist_end
        #update dictionary to reflect best stop for start and end
        distance_active = min_dist_start + min_dist_end
        best_route = Route(routes[route], 
                      closest_stop_to_start, 
                      closest_stop_to_end, 
                      distance_active)
        route_stop_ratings[route] = best_route
    return route_stop_ratings


def get_muni_path_info(routes_info, route, start_tag, end_tag, return_type): 

    #obtain list of stops to traverse   
        #(inbetween closest_stop_to_start and closest_stop_to_end)   
    droute_stop_tags = [stop.tag for stop in routes_info[route]]
    #print "droute_stop_tags:" , droute_stop_tags, start_tag, end_tag
    #for now assume each route passes each stop only once
    start_index = droute_stop_tags.index(start_tag)
    end_index = droute_stop_tags.index(end_tag)
    #print "start_index, stop_index" , start_index, end_index
    if start_index <= end_index:
        indices = range(start_index, end_index+1)
    #wrap around list if starting stop is listed before ending stop
    elif  start_index > end_index:
        indices = (range(start_index, len(droute_stop_tags)) +
                   range(0, end_index+1))
    #print "list of indices " , indices
    #obtain sum of distances between each stops and also keep track of path
    muni_distance = 0.
    path = []
    droute_stop_lats = [stop.lat for stop in routes_info[route]]
    droute_stop_lngs = [stop.lng for stop in routes_info[route]]
    for i, station_index in enumerate(indices):
        start_loc = (droute_stop_lats[station_index],
                 droute_stop_lngs[station_index])
        path.append(start_loc)
        if i+1 < len(indices):
            next_index = indices[i+1]
            #print "station_index, next_index" , station_index, next_index 
            end_loc = (droute_stop_lats[next_index],
                         droute_stop_lngs[next_index])
            dist = get_distance(start_loc, end_loc)
            #print dist
            muni_distance += dist
    if return_type == "distance":
        return muni_distance
    elif return_type == "path":
        return path


def get_muni_distance(routes_and_stops, routes_info):

    #for each (route, direction, start_stop, end_stop) combo, obtain:
        #distance traveled on muni
    muni_dist_for_routes = OrderedDict()
    for i_route, route in enumerate(routes_and_stops):
        if True: #route==('21', '21___O_F00'):
            start_tag = routes_and_stops[route].start.tag
            end_tag = routes_and_stops[route].end.tag    
            muni_dist =  get_muni_path_info(routes_info, route, start_tag, 
                                                end_tag, "distance")
            muni_dist_for_routes[route] = muni_dist

    return muni_dist_for_routes


def get_best_path(desired_trip, routes, routes_info, objective, active_speed, X):
    """Find best path for desired route."""

    #obtain measures of how good each route is, given desired trip
    #for each bus route
        #find closest stop to start location
        #find closest stop to end location
        #calculate total distance on foot/bike using the closest stops.     
    closest_stops = find_closest_stops(desired_trip, routes_info, routes)
    #get muni travel time for the routes and stops in routes_and_stops
    muni_dist_for_routes = get_muni_distance(closest_stops, routes_info)
    #toAdd:
        #arrival time to start_stop (start_stop_arrival_time)
        #arrival time to end_stop (end_stop_arrival_time)
        #dest_arrival_time (=end_stop_arrival_time + active_speed*min_dist_end)

    #create pandas dataframe containing best X routes
    indices = closest_stops.keys() + [(None, None)]
    rtitles = [closest_stops[r].title for r in closest_stops] + [(None, None)]
    closest_stops_to_start = [closest_stops[r].start for r in closest_stops] + [None]
    closest_stops_to_end = [closest_stops[r].end for r in closest_stops] + [None]
    distances_active_noMuni = get_distance((desired_trip.start_lat, 
                                            desired_trip.start_lng), 
                                            (desired_trip.end_lat,
                                            desired_trip.end_lng))
    travel_time_noMuni = (distances_active_noMuni/active_speed)*60
    distances_active = ([closest_stops[r].distance_active for r in closest_stops] 
                        + [distances_active_noMuni])
    distances_on_muni = [muni_dist_for_routes[r] for r in closest_stops] + [0]
    routes_ratings = pd.DataFrame.from_items([
                            ('rtitle',rtitles),
                            ('closest_stop_to_start',closest_stops_to_start),
                            ('closest_stop_to_end',closest_stops_to_end),
                            ('miles_active',distances_active),
                            ('miles_muni',distances_on_muni)])
    routes_ratings.index = indices
    #add estimated time in transit 
    muni_speed = 8.
    routes_ratings['minutes_in_transit'] = (
        routes_ratings['miles_active']/active_speed +
        routes_ratings['miles_muni']/muni_speed) * 60
    #add entry for situation in which no bus is taken

    routes_ratings_sorted = routes_ratings.sort_values(by=['minutes_in_transit'])
    best_x_routes = routes_ratings_sorted[:X]

    print "\n ****** We have found the best routes! ********** \n"
    print best_x_routes , "\n"

    print "Distance of desired trip: " , distances_active_noMuni
    print "Travel time if using only bike: " , travel_time_noMuni

    return best_x_routes


class RootMap:

    def __init__(self, boundaries):

        self.boundaries = boundaries

        f2, ax2 = plt.subplots(figsize=(10,6))

        lng0, lat0, lng1, lat1 = (self.boundaries[0], self.boundaries[1], 
                                 self.boundaries[2], self.boundaries[3]) 
        self.m = Basemap(lng0, lat0, lng1, lat1, resolution='h', ax=ax2)
        self.m.drawcoastlines()

        parallels = np.arange(lat0,lat1,abs(lat1-lat0)/15.0)
        self.m.drawparallels(parallels, labels=[1,0,0,0], fontsize=8)
        # draw meridians
        meridians = np.arange(lng0, lng1, abs(lng1-lng0)/15.0)
        self.m.drawmeridians(meridians, labels=[0,0,0,1], fontsize=8, rotation=25)

    def add_start_loc(self, lat, lng):
        start = self.m.scatter(lng, lat, s=5, color='green', alpha=.5)
        plt.text(lng, lat, "start", color='green', fontsize=10)

    def add_end_loc(self, lat, lng):
        end = self.m.scatter(lng, lat, s=5, color='red', alpha=.5)
        plt.text(lng, lat, "end", color='red', fontsize=10)


def get_map_boundaries(route):
    lng0, lng1, lat0, lat1 = [
        min(route.start_lng, route.end_lng) - 0.05, 
        max(route.start_lng, route.end_lng) + 0.05, 
        min(route.start_lat, route.end_lat) - 0.05, 
        max(route.start_lat, route.end_lat) + 0.05]
    boundaries =  [lng0, lat0, lng1, lat1]
    return boundaries


def get_path_from_google_dirs(directions):
    steps = directions[0]['legs'][0]['steps']
    bike_path = []
    for i_step, step in enumerate(steps):
        location = step['start_location']
        coordinates = (location['lat'], location['lng'])
        bike_path.append(coordinates)
        #last round, add end_location
        if i_step == len(steps)-1:
            location = step['end_location']
            coordinates = (location['lat'], location['lng'])
            bike_path.append(coordinates)    
    #print "bike_path: " , bike_path
    return bike_path


def draw_path_with_muni(mymap, gmaps, best_paths, droutes_info,
                        start_lat, start_lng, end_lat, end_lng):
    print "Suggested muni route is in red."
    muni_start_lat = best_paths['closest_stop_to_start'][0].lat
    muni_start_lng = best_paths['closest_stop_to_start'][0].lng
    muni_end_lat = best_paths['closest_stop_to_end'][0].lat
    muni_end_lng = best_paths['closest_stop_to_end'][0].lng
    mymap.addpoint(muni_start_lat, muni_start_lng, "#FF0000")
    mymap.addpoint(muni_end_lat, muni_end_lng, "#FF0000")
    #obtain muni path using (route_tag, direction_tag), and stop_tags
    path = get_muni_path_info(
                    droutes_info, 
                    best_paths.index[0], 
                    best_paths['closest_stop_to_start'][0].tag,
                    best_paths['closest_stop_to_end'][0].tag,
                    "path")
    #print "muni path of winner: " , path
    mymap.addpath(path, "#FF0000")
    #biking path
    print "Suggested bike paths are in green and blue."
    dirs0 = gmaps.directions((start_lat, start_lng), 
                            (muni_start_lat, muni_start_lng),
                            mode='bicycling')
    bike_path0 = get_path_from_google_dirs(dirs0)
    mymap.addpath(bike_path0, '#00FF00')
    dirs1 = gmaps.directions((muni_end_lat, muni_end_lng), 
                            (end_lat, end_lng),
                            mode='bicycling')
    bike_path1 = get_path_from_google_dirs(dirs1)
    mymap.addpath(bike_path1, '#0000FF')


def create_map(gmaps, best_paths, droutes_info, 
               start_lat, start_lng, end_lat, end_lng):
    print "\nNow creating map!"
    mymap = pygmaps.maps(start_lat, start_lng, 13)
    print "Start location is in green, end location in blue."
    mymap.addpoint(start_lat, start_lng, "#00FF00") #green
    mymap.addpoint(end_lat, end_lng, "#0000FF") #blue

    #muni routing
    if best_paths['miles_muni'][0] > 0:
        draw_path_with_muni(mymap, gmaps, best_paths, droutes_info, 
                            start_lat, start_lng, end_lat, end_lng)
    #if best route is to not take muni, then map bike path from start to end
    else:
        dirs = gmaps.directions((start_lat, start_lng), (end_lat, end_lng),
                                mode='bicycling')
        bike_path = get_path_from_google_dirs(dirs)
        mymap.addpath(bike_path, '#00FF00')

    mymap.draw('../mymap.html')


def main():

    gmaps = googlemaps.Client(key='AIzaSyAlKIryWGr0hfX45fX3Um-TiOk0yEXy0pA')

    agency_tag = "sf-muni"

    #desired Trip consists for start_lat, start_lng, end_lat, end_lng
    start_lat, start_lng = 37.773972, -122.451297
    end_lat, end_lng =  37.7933, -122.4067
    desired_trip = Trip(start_lat, start_lng, end_lat, end_lng)
    #address_start = gmaps.reverse_geocode((start_lat, start_lng))
    #address_end = gmaps.reverse_geocode((end_lat, end_lng))
    #print "start and end addresses" , address_start, address_end
    #dirs = gmaps.directions("1117 Montgomery St., San Francisco, CA", 
    #                        "2300 Harrison St., San Francisco, CA", 
    #                        mode="bicycling")
    #290 De Haro St, San Francisco, CA 94103, USA

    #choose to minimize either time_in_transit or arrival_time
    objective = 'minutes_in_transit'
    #objective = 'dest_arrival_time'
    #choose speed of travel when walking or biking (miles/hr) 
    active_speed = 4.
    #choose number of recommended routes to return
    num_suggestions = 10

    #obtain route list containing route tags and titles.
    routes =  get_routes(agency_tag)
    #obtain route/direction list containing tags and titles of each combo
    droutes = get_directed_routes(agency_tag)
    #obtain map from route_tag/stop_tag to stop info (title and location)
    stops_info = get_stop_info(agency_tag, routes)
    #obtain (route, direction) combos mapped to info on stops
    droutes_info = get_droute_info(agency_tag, routes, stops_info)   
    #return best path (muni route name, direction, start and stop locations)
        #best path has no transfers and minimizes total travel time
    best_paths = get_best_path(desired_trip, droutes, droutes_info,  
                              objective, active_speed, num_suggestions) 
    #create maps
    create_map(gmaps, best_paths, droutes_info, 
               start_lat, start_lng, end_lat, end_lng)

    #features to add:
        #improve travel times for bus paths (use google API?)
        #incorporate real-time departure times to minimize ETAs
            #See "prediction" section in NextBus documentation
        #allow future trip planning using static bus departure schedule
            #See "schedule" section in NextBus documentation
        #incorporate BART and caltrain
        #incorporate city bike share stations.
        #improve map view of suggested route (labels, precise bus path)
        #allow user to enter street address rather than lng/lat 
            # http://py-googlemaps.sourceforge.net/ 
        #allow for transit transfers

if __name__ == '__main__':
    main()

