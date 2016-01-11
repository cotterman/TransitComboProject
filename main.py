################################################################################
###################### The Transit Combo Project  ##############################
################################################################################
import urllib2
import numpy as np
import pandas as pd
import matplotlib as mpl
print "Version of matplotlib: " , mpl.__version__   #1.4.3
from mpl_toolkits.basemap import Basemap 
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET

from collections import namedtuple
Trip = namedtuple("Trip", ["start_lat", "start_lng", "end_lat", "end_lng"])
Stop = namedtuple("Stop", ["title", "lat", "lng"])
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

def get_stops_in_route(agency_tag, route_tag):
    route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
                  agency_tag + "&r=" + route_tag)
    result = urllib2.urlopen(route_page).read()
    route_root = ET.fromstring(result)
    #route_root has only one child.  
    assert len(route_root)==1
    route = route_root[0] #get to the child, which has all the route info.
    loc_list = [] 
    #notes on iterators:
        #iter(route) will just iterate of direct children (not grandchildren).
        #route.iter() iterates over all descendants in order of doc appearance.
        #for loop default is to use iter(route), giving direct children only
    for stop in route:
        if stop.tag == 'stop':
            stop = Stop(stop.attrib['title'], 
                        float(stop.attrib['lat']), 
                        float(stop.attrib['lon']))
            loc_list.append(stop)
            #print "location: " , location
    return loc_list

def get_stops(agency_tag, routes):

    #for each route, obtain pickup/dropoff locations
    locations = {}
    for route in routes:
        locations[route] = get_stops_in_route(agency_tag, route)
    #print "locations: " , locations
    #print "location_dict keys: " , locations.keys()
    #print "location_dict['N']: " , locations['N']
    return locations
    

def get_distance((lat0, lng0), (lat1, lng1)):
    """Calculate the manhattan distance between 2 points."""
    alpha = 84.2
    beta = 111.2
    distance = alpha*abs(lng1-lng0) + beta*abs(lat1-lat0)
    return distance


def find_closest_stops(desired_trip, routes_info, routes):
    """For each route, find closest stops to desired trip."""
    route_stop_ratings = {}
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


def get_muni_travel_time(agency_tag, routes_and_stops, active_speed):

    #expand each route by number of possible directions for that route
    for route in routes_and_stops:
        #print "route: ", route
        route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
                      agency_tag + "&r=" + route)
        result = urllib2.urlopen(route_page).read()
        route_root = ET.fromstring(result)
        directions_list = [] 
        assert len(route_root)==1
        #for direction in next(iter(route_root)):

    #for each (route, direction, start_stop, end_stop) combo, obtain:
        #arrival time to start_stop (start_stop_arrival_time)
        #arrival time to end_stop (end_stop_arrival_time)
        #muni_travel_time
        #time_in_transit (=muni_travel_time + active_speed*distance_active)
        #dest_arrival_time (=end_stop_arrival_time + active_speed*min_dist_end)

    return routes_and_stops


def rate_routes(agency_tag, desired_trip, routes_info, routes, active_speed):
    """ Create dictionary containing goodness measure for each route."""
    #for each bus route
        #find closest stop to start location
        #find closest stop to end location
        #calculate total distance on foot/bike using the closest stops.     
    routes_and_stops = find_closest_stops(desired_trip, routes_info, routes)
    #get minimum muni travel time for the routes and corresponding stops
    routes_and_travel_times = get_muni_travel_time(agency_tag, routes_and_stops, active_speed)

    return routes_and_travel_times


def get_best_path(agency_tag, desired_trip, routes_info, routes, objective, active_speed, X):
    """Find best path for desired route."""

    #obtain measure of how good each route is, given desired trip
    routes_ratings = rate_routes(agency_tag, desired_trip, routes_info, routes, active_speed)   

    #create pandas dataframe containing best X routes
    indices = routes_ratings.keys()
    rtitles = [routes_ratings[r].title for r in routes_ratings]
    closest_stops_to_start = [routes_ratings[r].start for r in routes_ratings]
    closest_stops_to_end = [routes_ratings[r].end for r in routes_ratings]
    distances_active = [routes_ratings[r].distance_active for r in routes_ratings]
    routes_ratings_df = pd.DataFrame.from_items([
                            ('rtitle',rtitles),
                            ('closest_stop_to_start',closest_stops_to_start),
                            ('closest_stop_to_end',closest_stops_to_end),
                            ('distance_active',distances_active)])
    routes_ratings_df.index = indices
    #todo: instead of distance_active, use objective ('time_in_transit' or 'dest_arrival_time')
    routes_ratings_sorted = routes_ratings_df.sort_values(by=['distance_active'])
    best_x_routes = routes_ratings_sorted[:X]

    print "\n ****** We have found the best routes! ********** \n"
    print best_x_routes

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

def main():

    agency_tag = "sf-muni"

    #desired Trip consists for start_lat, start_lng, end_lat, end_lng
    start_lat = 37.773972
    start_lng = -122.431297
    end_lat =  37.7833
    end_lng = -122.4167
    desired_trip = Trip(start_lat, start_lng, end_lat, end_lng)

    #choose to minimize either time_in_transit or arrival_time
    objective = 'time_in_transit'
    #objective = 'dest_arrival_time'

    #choose speed of travel when walking or biking (miles/hr) 
    active_speed = 10

    #choose number of recommended routes to return
    num_suggestions = 3

    #map these locations on map
    map_bounds = get_map_boundaries(desired_trip)
    map = RootMap(map_bounds)
    map.add_start_loc(start_lat, start_lng)
    map.add_end_loc(end_lat, end_lng)
    plt.savefig('../'+"desired_trip")

    #map_data_old('desired_route_2.png', desired_trip)

    #obtain route list containing route tags and titles.
    #routes =  get_routes(agency_tag)

    #obtain possible pick-up/drop-off locations
        #include associated route title, stop title, stop_lat, stop_lon
    #routes_info = get_stops(agency_tag, routes)
    
    #return best path (muni route name, direction, start and stop locations)
        #best path has no transfers and minimizes total distance on foot/bike
        #not concerned about time spent on bus (for now)
    #best_path = get_best_path(agency_tag, desired_trip, routes_info, routes, 
    #                         objective, active_speed, num_suggestions) 

    #map.add_path(path)
    plt.savefig('../'+"suggest_route")

    #features to add:
        #incorporate travel times for bus paths 
            #find path that minimizes travel time
        #incorporate departure times 
            #find path that minimizes total time (travel + waiting)
        #allow for bus transfers
        #incorporate BART and caltrain
        #provide map view of suggested route
        #provide best 3 routes with ETAs
        #allow future trip planning using static bus schedule
        

if __name__ == '__main__':
    main()

