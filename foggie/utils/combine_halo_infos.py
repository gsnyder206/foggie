'''
Filename: combine_halo_infos.py
Author: Cassi
Last modified: 1/22/21
Reads in lots of hdf5 tables of halo catalog files, one per snapshot, and combines them all into one.
Requires the tables to be located in your system's output_path in get_run_loc_etc.py.
'''

import numpy as np
from astropy.table import Table, vstack
import os
import argparse
from foggie.utils.get_run_loc_etc import get_run_loc_etc

def parse_args():
    '''Parse command line arguments. Returns args object.'''

    parser = argparse.ArgumentParser(description='Combines mass profile and satellite catalog files for individual outputs into a couple of big files.')

    # Optional arguments:
    parser.add_argument('--halo', metavar='halo', type=str, action='store', \
                        help='Which halo? Default is 8508 (Tempest)')
    parser.set_defaults(halo='8508')

    parser.add_argument('--run', metavar='run', type=str, action='store', \
                        help='Which run? Default is nref11c_nref9f')
    parser.set_defaults(run='nref11c_nref9f')

    parser.add_argument('--system', metavar='system', type=str, action='store', \
                        help='Which system are you on? Default is cassiopeia')
    parser.set_defaults(system='cassiopeia')

    parser.add_argument('--pwd', dest='pwd', action='store_true',
                        help='Just use the working directory?, Default is no')
    parser.set_defaults(pwd=False)

    parser.add_argument('--which', metavar='which', type=str, action='store', \
                        help='Which set of tables do you want to combine? Options are:\n' + \
                        'masses, satellites, or both, and default is to do both.')
    parser.set_defaults(which='both')

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    print(args.halo)
    print(args.run)
    print(args.system)
    foggie_dir, output_dir, run_dir, code_path, trackname, haloname, spectra_dir, infofile = get_run_loc_etc(args)

    #################################################
    # Masses:
    if (args.which=='both') or (args.which=='masses'):
        table_loc = output_dir + 'masses_halo_00' + args.halo + '/' + args.run + '/'

        sfr_list = []
        snap_list = []
        redshift_list = []
        all_files = os.listdir(table_loc)
        catalog_files = []
        for i in range(len(all_files)):
            if (all_files[i][:2]=='DD') or (all_files[i][:2]=='RD'):
                catalog_files.append(all_files[i])
        big_table1 = None
        big_table2 = None
        for filename in catalog_files:
            data = Table.read(table_loc + '/' + filename, path='all_data')
            snap_list.append(filename[:6])
            redshift_list.append(data['redshift'][0])
            sfr_list.append(data['sfr'][np.where(data['radius']>20.)[0][0]])
            data.remove_column('sfr')
            if (data['redshift'][0]>2.):
                if (big_table1 == None):
                    big_table1 = data
                else:
                    big_table1 = vstack([big_table1, data])
            if (data['redshift'][0]<=2.):
                if (big_table2 == None):
                    big_table2 = data
                else:
                    big_table2 = vstack([big_table2, data])
        if (big_table1): big_table1.write(code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/' + 'masses_z-gtr-2.hdf5', path='all_data', serialize_meta=True, overwrite=True)
        if (big_table2): big_table2.write(code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/' + 'masses_z-less-2.hdf5', path='all_data', serialize_meta=True, overwrite=True)
        redshift_s, snap_s, sfr_s = map(list, zip(*sorted(zip(redshift_list, snap_list, sfr_list), reverse=True)))
        f = open(code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/sfr', 'w')
        f.write('#Snap     z           SFR (Msun/yr)\n')
        for i in range(len(snap_s)):
            f.write('%s    %.6f    %.6f\n' % (snap_s[i], redshift_s[i], sfr_s[i]))
        f.close()
    #################################################

    #################################################
    # Satellites:
    if (args.which=='both') or (args.which=='satellites'):
        table_loc = output_dir + 'satellites_halo_00' + args.halo + '/' + args.run + '/'

        sfr_list = []
        snap_list = []
        redshift_list = []
        all_files = os.listdir(table_loc)
        catalog_files = []
        for i in range(len(all_files)):
            if (all_files[i][:2]=='DD') or (all_files[i][:2]=='RD'):
                catalog_files.append(all_files[i])
        big_table = Table(names=('snap', 'sat_id', 'sat_x', 'sat_y', 'sat_z'), \
                     dtype=('S6', 'i2', 'f8', 'f8', 'f8'))
        for filename in catalog_files:
            sat_id, sat_x, sat_y, sat_z = np.loadtxt(table_loc + '/' + filename, \
              unpack=True, usecols=[0,1,2,3])
            for j in range(len(sat_id)):
                big_table.add_row([filename[:6], sat_id[j], sat_x[j], sat_y[j], sat_z[j]])
        table_units = {'snap':None,'sat_id':None,'sat_x':'kpc','sat_y':'kpc','sat_z':'kpc'}
        for key in big_table.keys():
            big_table[key].unit = table_units[key]
        big_table.write(code_path + 'halo_infos/00' + args.halo + '/' + args.run + '/' + 'satellites.hdf5', path='all_data', serialize_meta=True, overwrite=True)
    #################################################
