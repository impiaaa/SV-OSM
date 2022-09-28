import sys
from math import floor, ceil
mnlat = 37.1227145
mxlat = 37.4692112
mnlon = -122.0538173
mxlon = -121.5861383
divisions = int(sys.argv[1])
def interp(i, mn, mx):
    return i*(mx-mn)/divisions+mn
scale = (10**7)
for ilat in range(divisions):
    for ilon in range(divisions):
        print("  <bounds minlat='%.7f' minlon='%.7f' maxlat='%.7f' maxlon='%.7f' origin='OpenStreetMap server' />"%\
        (floor(interp(ilat, mnlat, mxlat)*scale)/scale,
         floor(interp(ilon, mnlon, mxlon)*scale)/scale,
         ceil(interp(ilat+1, mnlat, mxlat)*scale)/scale,
         ceil(interp(ilon+1, mnlon, mxlon)*scale)/scale))

