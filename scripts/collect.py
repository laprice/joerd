#!/usr/bin/env python
from math import log, tan, pi
from itertools import product

def mercator(lat, lon, zoom):
    ''' Convert latitude, longitude to z/x/y tile coordinate at given zoom.
        
        >>> mercator(0, 0, 0)
        (0, 0, 0)
        
        >>> mercator(0, 0, 16)
        (16, 32768, 32768)
        
        >>> mercator(37.79125, -122.39197, 16)
        (16, 10487, 25327)

        >>> mercator(40.74418, -73.99047, 16)
        (16, 19298, 24632)

        >>> mercator(-35.30816, 149.12446, 16)
        (16, 59915, 39645)
    '''
    # convert to radians
    x1, y1 = lon * pi/180, lat * pi/180
    
    # project to mercator
    x2, y2 = x1, log(tan(0.25 * pi + 0.5 * y1))
    
    # transform to tile space
    tiles, diameter = 2 ** zoom, 2 * pi
    x3, y3 = int(tiles * (x2 + pi) / diameter), int(tiles * (pi - y2) / diameter)
    
    return zoom, x3, y3

def tiles(zoom, lat1, lon1, lat2, lon2):
    ''' Convert geographic bounds into a list of tile coordinates at given zoom.
        
        >>> tiles(16, 37.79125, -122.39197, 37.79125, -122.39197)
        [(16, 10487, 25327)]

        >>> tiles(16, 0.00034, -0.00056, -0.00034, 0.00043)
        [(16, 32767, 32767), (16, 32768, 32767), (16, 32767, 32768), (16, 32768, 32768)]

        >>> tiles(16, -0.00034, 0.00043, 0.00034, -0.00056)
        [(16, 32767, 32767), (16, 32768, 32767), (16, 32767, 32768), (16, 32768, 32768)]
    '''
    # convert to geographic bounding box
    minlat, minlon = min(lat1, lat2), min(lon1, lon2)
    maxlat, maxlon = max(lat1, lat2), max(lon1, lon2)
    
    # convert to tile-space bounding box
    _, xmin, ymin = mercator(maxlat, minlon, zoom)
    _, xmax, ymax = mercator(minlat, maxlon, zoom)
    
    # generate a list of tiles
    xs, ys = range(xmin, xmax+1), range(ymin, ymax+1)
    tiles = [(zoom, x, y) for (y, x) in product(ys, xs)]
    
    return tiles

if __name__ == '__main__':
    import doctest
    doctest.testmod()
