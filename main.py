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

def map_data(fname, route):
    
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
    print "parallels" , parallels
    m.drawparallels(
        parallels, labels=[1,0,0,0], fontsize=8)
    # draw meridians
    meridians = np.arange(lng0, lng1, abs(lng1-lng0)/15.0)
    print "meridians" , meridians
    m.drawmeridians(
        meridians, labels=[0,0,0,1], fontsize=8, rotation=25)

    #m.drawmapboundary(fill_color='lightblue')
    #m.fillcontinents(color='lightgrey', lake_color='lightblue')

    # Scatter plot of vehicle starts and ends 
    start = m.scatter(route.start_lng, route.start_lat, 
                       s=5, color='forestgreen', alpha=.5)
    end = m.scatter(route.end_lng, route.end_lat,  
                     s=5, color='darkorchid', alpha=.5)
    #ax2.legend((starts, ends), ('Start location', 'End location'),
    #          loc = 'lower right',title="", scatterpoints=1, fontsize=10)

    # Add optimal routs to plot
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
	for route in agency_root:
		rtag = route.get('tag')
		rtitle = route.get('title')
		routes[rtag] = rtitle
	return routes


def get_stops(agency_tag, routes):

	#for each route, obtain pickup/dropoff locations
	locations = {}
	for route in routes:
		#print "route: " , route
		route_page = ("http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=" +
					  agency_tag + "&r=" + route)
		result = urllib2.urlopen(route_page).read()
		route_root = ET.fromstring(result)
		loc_list = [] 
		assert len(route_root)==1
		for stop in next(iter(route_root)):
			if 'lat' in stop.attrib:
				stop = Stop(stop.attrib['title'], 
							float(stop.attrib['lat']), 
							float(stop.attrib['lon']))
				loc_list.append(stop)
				#print "location: " , location
		locations[route] = loc_list
	#print "location_dict keys: " , location_dict.keys()
	#print "location_dict['F']: " , location_dict['F']
	return locations
	

def get_distance((lat0, lng0), (lat1, lng1)):
	"""Calculate the manhattan distance between 2 points."""
	alpha = 84.2
	beta = 111.2
	distance = alpha*abs(lng1-lng0) + beta*abs(lat1-lat0)
	return distance

def rate_routes(desired_trip, routes_info, routes):
	"""	Create dictionary containing goodness measure for each route."""
	#for each bus route
		#find closest stop to start location
		#find closest stop to end location
		#calculate total distance on foot/bike using the closest stops. 
	routes_ratings = {}
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
		routes_ratings[route] = best_route
	return routes_ratings	


def get_best_path(desired_trip, routes_info, routes, X=1):
	"""Find best path for desired route."""

	#obtain measure of how good each route is, given desired trip
	routes_ratings = rate_routes(desired_trip, routes_info, routes)	

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
	routes_ratings_sorted = routes_ratings_df.sort_values(by=['distance_active'])
	best_x_routes = routes_ratings_sorted[:X]

	return best_x_routes


def main():

	agency_tag = "sf-muni"

	#desired Trip consists for start_lat, start_lng, end_lat, end_lng
	start_lat = 37.773972
	start_lng = -122.431297
	end_lat =  37.7833
	end_lng = -122.4167
	desired_trip = Trip(start_lat, start_lng, end_lat, end_lng)

	#map these locations on map
	map_data('desired_route_2.png', desired_trip)

	#obtain route list containing route tags and titles.
	routes =  get_routes(agency_tag)

	#obtain possible pick-up/drop-off locations
		#include associated route title, stop title, stop_lat, stop_lon
	routes_info = get_stops(agency_tag, routes)
	
	#return best path (muni route name, direction, start and stop locations)
		#best path has no transfers and minimizes total distance on foot/bike
		#not concerned about time spent on bus (for now)
	best_path = get_best_path(desired_trip, routes_info, routes, 3)	
	print "\n ****** We have found the best routes! ********** \n"
	print best_path

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

