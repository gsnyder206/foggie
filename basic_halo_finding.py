"""
This module provides basic halo finding capability to FOGGIE.
Started January 2019 by JT.
"""

import yt
from yt.units.yt_array import YTArray
from yt.funcs import mylog
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datashader as dshader
import datashader.transfer_functions as tf
import multiprocessing as mp
from astropy.cosmology import WMAP9

def get_box_density(dataset):
    """ gets the total box density in Msun / Mpc***3 for a yt dataset"""
    return WMAP9.critical_density(0).value * \
                    (3.086e24)**3 / 1.989e33 * dataset.omega_matter \
                    * YTArray(1., 'Msun') / YTArray(1., 'Mpc')**3


def create_particle_df(box):
    """ extracts particle data from a yt region and returns a DataFrame
        with the positions and particle masses for further processing"""

    particle_data = {}
    particle_data['position_x'] = (box['particle_position_x'].in_units('kpc')).ndarray_view() * 0.695
    particle_data['position_y'] = (box['particle_position_y'].in_units('kpc')).ndarray_view() * 0.695
    particle_data['position_z'] = (box['particle_position_z'].in_units('kpc')).ndarray_view() * 0.695
    print("Done with particle physical positions")

    particle_data['code_x'] = box['particle_position_x']
    particle_data['code_y'] = box['particle_position_y']
    particle_data['code_z'] = box['particle_position_z']
    print("Done with particle code positions")

    particle_data['mass'] = (box['particle_mass'].in_units('Msun')).ndarray_view()
    print("Done with particle masses")

    particle_df = pd.DataFrame.from_dict(particle_data)
    particle_df.index = box['particle_index'] #<---- sets df index to particle index, convenient later.
    particle_df['halo_id_number'] = particle_df['position_x'] * 0.
    print("Done with particle indices")

    particle_df['x_proj_density'] = particle_df['position_x'] * 0.
    particle_df['y_proj_density'] = particle_df['position_y'] * 0.
    particle_df['z_proj_density'] = particle_df['position_z'] * 0.
    particle_df['sum_proj_density'] = particle_df['position_x'] * 0.
    print("Done with particle masses")


    halo_cat_dict = {'x0': [0., 0.], 'y0':[0.0, 0.0], 'z0':[0.0,0.0],
                 'mass': [0.0, 0.0], 'r200': [0.0, 0.0],
                 'sum_dens': [0.0, 0.0], 'key_particle': 0., 'n_particles':0.0}

    halo_catalog = pd.DataFrame.from_dict(halo_cat_dict)

    #<---- will now create a "blank" dataframe with just hte first particle
    #<---- in which we will store the particles that get deleted from the
    #<---- main dataframe
    used_particles = particle_df.iloc[0:1]

    return particle_df, used_particles, halo_catalog


def aggregate_particles(df, axis1, axis2, bincount):
    """ Uses datashader's points aggregator to produce a 2D histogram"""
    #<---- note that the "bins" are 100,000 / 1000 comoving kpc, or 100 cKpc in each dimension
    cvs = dshader.Canvas(plot_width=bincount, plot_height=bincount,
        x_range=[0,25000], y_range=[0,25000])
    agg = cvs.points(df, axis1, axis2, dshader.sum('mass'))
    agg = agg.fillna(0.) #<---- this is necessary because agg contains empty bins as NaNs

    return agg



def assign_densities(particle_df):
    """ Assign 2D projected densities to each particle in the dataframe
        Sum those densities and put them all into the dataframe."""

    #<---- aggregate the particles and populate the projected 2D density
    #<---- fields of the dataframe Z projection, so axis1 = x, axis2=y,
    #<---- flip for subscripts
    agg_z = aggregate_particles(particle_df, 'position_x', 'position_y', 2500)
    densities = agg_z.values
    xsubs = np.floor(particle_df['position_x']/10.).astype(int)
    ysubs = np.floor(particle_df['position_y']/10.).astype(int)
    zsubs = np.floor(particle_df['position_z']/10.).astype(int)
    particle_df['z_proj_density'] = densities[ysubs, xsubs]

    #<---- Y projection, so axis1 = x, axis2=z, flip for subscripts
    agg_y = aggregate_particles(particle_df, 'position_x', 'position_z', 2500)
    densities = agg_y.values
    particle_df['y_proj_density'] = densities[zsubs, xsubs]

    #<---- X projection, so axis1 = y, axis2=z, flip for subscripts
    agg_x = aggregate_particles(particle_df, 'position_y', 'position_z', 2500)
    densities = agg_x.values
    particle_df['x_proj_density'] = densities[zsubs, ysubs]

    particle_df['sum_proj_density'] = particle_df['x_proj_density'] + \
                                      particle_df['y_proj_density'] + \
                                      particle_df['z_proj_density']

    particle_df.sort_values('sum_proj_density', ascending=False, inplace=True)

    print("Done assigning densities: ")

    return {'agg_x':agg_x, 'agg_y':agg_y, 'agg_z':agg_z}, particle_df



def halo_r200_guess(sigma):
    return 10.**(0.4 * np.log10(sigma) - 2.) / 1000.
    #<---- provides a guess, in proper Mpc, for R200 based on the tabulated sum_proj_density



def obtain_rvir(dataset, first_particle_position, total_box_density, central_sigma):

    print("central sigma ", central_sigma)
    print("R200 guess ", halo_r200_guess(central_sigma) )

    radius = halo_r200_guess(central_sigma)
    sph = dataset.sphere(first_particle_position, (radius, 'Mpc') )
    halo_mass = sph['particle_mass'].sum().in_units('Msun')
    halo_vol = 4. / 3. * 3.14159 * YTArray(radius, 'Mpc')**3
    overdensity = halo_mass / halo_vol / total_box_density
    print("initial overdensity at guess radius R = ", radius, " overdensity: ", overdensity)

    if (overdensity > 200): #<---- if overdensity > 200, work *out* in radius
        while overdensity > 200.:
            increment = 1.1
            if np.abs(overdensity - 200.) < 20: increment = 1.05
            radius = radius * increment #<---- step out by 10 %
            sph = dataset.sphere(first_particle_position, (radius, 'Mpc') )
            halo_mass = sph['particle_mass'].sum().in_units('Msun')
            halo_vol = 4. / 3. * 3.14159 * YTArray(radius, 'Mpc')**3
            overdensity = halo_mass / halo_vol / total_box_density
            print("stepping out from guess, radius R = ", radius, " overdensity: ", overdensity)
    elif (overdensity < 200):  #<---- if overdensity < 200, work *in* in radius
        while overdensity < 200.:
            increment = 0.9
            if np.abs(overdensity - 200.) < 20: increment = 0.95
            radius = radius * increment #<---- step in by 5 kpc
            sph = dataset.sphere(first_particle_position, (radius, 'Mpc') )
            halo_mass = sph['particle_mass'].sum().in_units('Msun')
            halo_vol = 4. / 3. * 3.14159 * YTArray(radius, 'Mpc')**3
            overdensity = halo_mass / halo_vol / total_box_density
            print("stepping in from guess, radius R = ", radius, " overdensity: ", overdensity)

    return halo_mass, radius




def find_a_halo(dataset, particle_df, used_particles, halo_catalog, total_box_density):

    #<---- first we reassign densities based on the current particle dataframe
    agg_dict, particle_df = assign_densities(particle_df)

    #<---- assume for now that the first particle is the new halo center
    first_particle_index = particle_df.index.values[0]
    first_particle_position = [particle_df['code_x'][first_particle_index],
                               particle_df['code_y'][first_particle_index],
                               particle_df['code_z'][first_particle_index]]
    central_sigma = particle_df['sum_proj_density'][first_particle_index]

    halo_mass, radius = obtain_rvir(dataset, first_particle_position, total_box_density, central_sigma)

    print("FAH, with Mass :", halo_mass.value/1e12, 'e12 Msun and radius :', radius, 'Mpc')

    sph = dataset.sphere(first_particle_position, (radius, 'Mpc') )

    sph.save_as_dataset(filename = 'halo_'+str(int(first_particle_index))+'.h5',
        fields = ["particle_position_x", "particle_position_y", "particle_position_z",
                  "particle_index", "particle_mass"])
        #<---- these filenames should always be unique since no two halos should
        # have the same key particle

    pindex = sph['particle_index']

    ss = particle_df['sum_proj_density'][first_particle_index]

    print("FAH adding ", pindex.size, " to used_particles from the dataframe")
    used_particles = used_particles.append(particle_df.loc[pindex])

    print("FAH dropping ", pindex.size, " particles from the dataframe")
    particle_df.drop(pindex, inplace=True, errors='ignore') #<---- ignore means particles that don't exist will be ignored.

    hh = pd.DataFrame([[first_particle_position[0], first_particle_position[1],
                         first_particle_position[2], halo_mass.value, radius,
                         ss, first_particle_index, pindex.size]],
                         columns=['x0','y0','z0','mass','r200', 'sum_dens', 'key_particle', 'n_particles'])

    return particle_df, used_particles, hh, pindex




def find_halos_in_region(dsname, minsigma, qnumber, x0, y0, z0, x1, y1, z1):

    print("Analyzing Octant : ", qnumber)
    dataset = yt.load(dsname)
    box = dataset.r[x0:x1, y0:y1, z0:z1]
    particle_df, used_particles, halo_catalog = create_particle_df(box)
    agg_dict, particle_df = assign_densities(particle_df)
    while (np.max(particle_df['sum_proj_density']) > minsigma):
        particle_df, used_particles, hh, pindex = find_a_halo(dataset, particle_df, used_particles, halo_catalog, get_box_density(dataset))
        halo_catalog = halo_catalog.append(hh, ignore_index=True)
        print("Halo in octant: ", qnumber, hh)

    halo_catalog = halo_catalog[2:]
    halo_catalog.to_pickle('halo_octant_'+str(qnumber)+'.pkl' )
    used_particles.to_pickle('used_particles_'+str(qnumber)+'.pkl' )

    return halo_catalog





def get_subregions(dsname, minsigma, interval):
    """ return a list of subregions that carve up the domain into
        (1/interval)**3 yt regions that will be multithreaded"""
    count = 0
    list_of_regions = [(0,0,0,0,0,0,0,0)]
    for i in np.arange(1./ interval):
        for j in np.arange(1./ interval):
            for k in np.arange(1./ interval):
                this_tuple = (dsname, minsigma, count, i*interval, j*interval, k*interval,
                        i*interval+interval, j*interval+interval, k*interval+interval )
                count += 1
                list_of_regions.append(this_tuple)
    return list_of_regions[1:]




def drive_halo_finding(dsname, minsigma, interval, n_processes):
    """ This is the main function call to drive halo finding.
    Parameters are the dataset name, the minimum projected density
    to count as halos, and the dx/dy/dz interval for the subregions
    that will be multithreaded."""

    subregion_list = get_subregions(dsname, minsigma, interval)
    pool = mp.Pool(processes=n_processes)
    list_of_halos = pool.starmap(find_halos_in_region, subregion_list)
    return list_of_halos
