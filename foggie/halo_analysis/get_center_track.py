
""" this is FOGGIE's main routine for generating a halo track from an
  initial guess and a set of snapshots - JT and MSP"

import yt
from astropy.table import Table
from astropy.io import ascii

from foggie.utils.consistency  import  *
from foggie.utils.get_halo_center import get_halo_center
import numpy as np


def get_center_track(first_center, latesnap, earlysnap, interval):

    ### do this way at high-redshift
    ### snaplist = np.flipud(np.arange(earlysnap,latesnap+1))

    ### do this way at later times
    snaplist = np.arange(earlysnap,latesnap+1)
    print(snaplist)

    t = Table([[0.0,0.0],[0.0,0.0],[0.0,0.0],[0.0,0.0], ['       ', '       ']],
        names=('redshift', 'x0', 'y0', 'z0', 'name'))

    center_guess = first_center
    search_radius = 10. ### COMOVING KPC

    for isnap in snaplist:
        if (isnap > 999): name = 'DD'+str(isnap)
        if (isnap <= 999): name = 'DD0'+str(isnap)
        if (isnap <= 99): name = 'DD00'+str(isnap)
        if (isnap <= 9): name = 'DD000'+str(isnap)

        print
        print
        print(name)
        ds = yt.load(name+'/'+name)
        comoving_box_size = ds.get_parameter('CosmologyComovingBoxSize')
        print('Comoving Box Size:', comoving_box_size)

        # decreased these from 500 to 100 because outputs so short spaced now
        this_search_radius = search_radius / (1+ds.get_parameter('CosmologyCurrentRedshift'))  ## search radius is in PHYSICAL kpc
        new_center, vel_center = get_halo_center(ds, center_guess, radius=this_search_radius, vel_radius=this_search_radius)
        print(new_center)

        t.add_row( [ds.get_parameter('CosmologyCurrentRedshift'),
            new_center[0], new_center[1],new_center[2], name])

        center_guess = new_center

        p = yt.ProjectionPlot(ds, 'x', 'density', center=new_center, width=(200., 'kpc'))
        p.set_zlim('density', density_proj_min, density_proj_max)
        p.set_cmap(field='density', cmap=density_color_map)
        p.annotate_timestamp(corner='upper_left', redshift=True, draw_inset_box=True)
        p.save()
        p = yt.ProjectionPlot(ds, 'y', 'density', center=new_center, width=(200., 'kpc'))
        p.set_zlim('density', density_proj_min, density_proj_max)
        p.set_cmap(field='density', cmap=density_color_map)
        p.annotate_timestamp(corner='upper_left', redshift=True, draw_inset_box=True)
        p.save()
        p = yt.ProjectionPlot(ds, 'z', 'density', center=new_center, width=(200., 'kpc'))
        p.set_zlim('density', density_proj_min, density_proj_max)
        p.set_cmap(field='density', cmap=density_color_map)
        p.annotate_timestamp(corner='upper_left', redshift=True, draw_inset_box=True)
        p.save()
        print(t)
        ascii.write(t, 'track_temp.dat', format='fixed_width_two_line', overwrite=True)
        print
        print

        ### just in case memory becomes a problem
        ds.index.clear_all_data()
        del ds.index.grid_dimensions
        del ds.index.grid_left_edge
        del ds.index.grid_right_edge
        del ds.index.grid_levels
        del ds.index.grid_particle_count
        del ds.index.grids


    t = t[2:]
    print(t)

    # now interpolate the track to the interval given as a parameter
    n_points = int((np.max(t['redshift']) - np.min(t['redshift']))  / interval)
    newredshift = np.min(t['redshift']) + np.arange(n_points+2) * interval
    newx = np.interp(newredshift, t['redshift'], t['x0'])
    newy = np.interp(newredshift, t['redshift'], t['y0'])
    newz = np.interp(newredshift, t['redshift'], t['z0'])

    tt = Table([ newredshift, newx, newy, newz], names=('redshift','x','y','z'))

    t.write('track.fits',overwrite=True)
    tt.write('track_interpolate.fits',overwrite=True)

    ascii.write(t, 'track.dat', format='fixed_width_two_line', overwrite=True)
    ascii.write(tt, 'track_interpolate.dat', format='fixed_width_two_line', overwrite=True)

    return t, tt


if __name__ == "__main__":
    ## first_center is the center at the last output; working backwards

    ### DD0493 for nref11n_selfshield_z15
    ### first_center = [0.49400806427001953, 0.48881053924560547, 0.50222492218017578]
    ### first_center = [ 0.49400806427, 0.488810539246,  0.50222492218 ]

    ### DD0752 for nref11n_selfshield_z15
    # first_center = [0.493138313293, 0.485363960266, 0.503630638123 ]

    ### DD0999 for nref11n_selfshield_z15
    #first_center = [0.492419242859, 0.482583045959, 0.504755973816]

    ### DD1088 for nref11n_selfshield_z15
    #first_center = [0.492186546326, 0.481648445129, 0.505097389221]

    ### DD1547 for nref11n_selfshield_z15
    # first_center = [0.49123287200927734, 0.4774351119995117, 0.5069074630737305 ]

    ## DD1795
    # first_center = [0.49077320098876953, 0.4754419326782226, 0.5077409744262695]

    ## DD2183
    #first_center = [0.4901914596557618,  0.4727659225463867, 0.5089044570922852]

    ### DD0580 for halo 5016
    #first_center = [0.515818595886, 0.475518226624, 0.497570991516]

    ### DD0984 for halo 5016
    first_center = [ 0.5232095718383789, 0.46910381317138666,  0.5017900466918945 ]

    ### DD0580 for halo 5036
    #first_center = [0.485018730164, 0.502505302429, 0.503439903259]

    ### DD0580 for halo 2392
    #first_center = [0.497841835022, 0.497172355652, 0.479462623596]

    ### DD0580 for halo 2878
    # first_center = [0.508492469788, 0.509057044983, 0.489006996155]

    ### DD0580 for halo 4123
    # first_center = [0.485667228699, 0.478737831116, 0.485198020935]

    ### DD0689 for halo 5036
    # first_center = [0.4834909439086914, 0.5023832321166992, 0.5033254623413086 ]


    get_center_track(first_center, 1050, 984, 0.002)
