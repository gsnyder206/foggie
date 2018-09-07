"""
creates "core sample" velocity plots - JT 070318
"""
import copy
import datashader as dshader
import datashader.transfer_functions as tf
from datashader import reductions
import numpy as np
import pickle
import glob
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import trident
import yt
from astropy.io import fits
from matplotlib.gridspec import GridSpec
os.sys.path.insert(0, os.environ['FOGGIE_REPO'])
from consistency import new_phase_color_key, new_metals_color_key, species_dict, phase_color_labels, metal_color_labels
import astropy.units as u
mpl.rcParams['font.family'] = 'stixgeneral'
import foggie_utils as futils
import cmap_utils as cmaps
import cloud_utils as clouds

CORE_WIDTH = 20.

def show_velphase(ds, ray_df, ray_start, ray_end, hdulist, fileroot):
    """ oh, the docstring is missing, is it??? """

    df = futils.ds_to_df(ds, ray_start, ray_end)
    ray_index, axis_to_use, second_axis = futils.get_ray_axis(ray_start, ray_end)

    # establish the grid of plots and obtain the axis objects
    fig = plt.figure(figsize=(9, 6))
    fig.text(0.55, 0.04, r'Velocity [km s$^{-1}$]', ha='center', va='center')
    gs = GridSpec(2, 6, width_ratios=[1, 1, 5, 5, 5, 5], height_ratios=[4, 1])
    ax0 = plt.subplot(gs[0])
    ax0.set_title('T')
    ax1 = plt.subplot(gs[1])
    ax1.set_title('Z')
    ax2 = plt.subplot(gs[2])
    ax2.set_title(r'H I Ly$\alpha$')
    ax3 = plt.subplot(gs[3])
    ax3.set_title('Si II 1260')
    ax4 = plt.subplot(gs[4])
    ax4.set_title('C IV 1548')
    ax5 = plt.subplot(gs[5])
    ax5.set_title('O VI 1032')

    ax6 = plt.subplot(gs[6])
    ax6.spines["top"].set_color('black')
    ax6.spines["bottom"].set_color('white')
    ax6.spines["left"].set_color('white')
    ax6.spines["right"].set_color('white')

    ax7 = plt.subplot(gs[7])
    ax7.spines["top"].set_color('black')
    ax7.spines["bottom"].set_color('white')
    ax7.spines["left"].set_color('white')
    ax7.spines["right"].set_color('white')
    ax8 = plt.subplot(gs[8])
    ax9 = plt.subplot(gs[9])
    ax10 = plt.subplot(gs[10])
    ax11 = plt.subplot(gs[11])

    # add in the temperature and metallicity core sample renders
    for ax, label in zip([ax0, ax1], ['phase_label','metal_label']):
        color_keys = {'phase_label':new_phase_color_key, 'metal_label':new_metals_color_key}
        cvs = dshader.Canvas(plot_width=800, plot_height=200,
                                x_range=(np.min(df[axis_to_use]), np.max(df[axis_to_use])),
                                y_range=(np.mean(df[second_axis])-CORE_WIDTH/0.695,
                                         np.mean(df[second_axis])+CORE_WIDTH/0.695))
        agg = cvs.points(df, axis_to_use, second_axis, dshader.count_cat(label))
        img = tf.shade(agg, color_key=color_keys[label], how='eq_hist')
        img_to_show = tf.spread(img, px=2, shape='square')
        ax.imshow(np.rot90(img_to_show.to_pil()))

    ax0.set_ylabel('x [comoving kpc]', fontname='Arial', fontsize=10)
    ax0.set_yticks([0, 200, 400, 600, 800])
    ax0.set_yticklabels([str(int(s)) for s in [0, 50, 100, 150, 200]],
                        fontname='Arial', fontsize=8)

    # render x vs. vx but don't show it yet.
    cvs = dshader.Canvas(plot_width=800, plot_height=300,
                         x_range=(np.min(df[axis_to_use]),
                                  np.max(df[axis_to_use])),
                         y_range=(-350, 350))  # velocities range [-350,350]
    agg = cvs.points(df, axis_to_use, 'v'+axis_to_use,
                     dshader.count_cat('phase_label'))
    x_vx_phase = tf.spread(
        tf.shade(agg, color_key=new_phase_color_key), shape='square')

    # now iterate over the species to get the ion fraction plots
    for species, ax in zip(['HI', 'SiII', 'CIV', 'OVI'], [ax2, ax3, ax4, ax5]):

        print("Current species: ", species)
        cvs = dshader.Canvas(plot_width=800, plot_height=300,
                             y_range=(-350, 350),
                             x_range=(ray_start[ray_index],
                                      ray_end[ray_index]))
        vx_points = cvs.points(ray_df, axis_to_use,
                               axis_to_use + '-velocity',
                               agg=reductions.mean(species_dict[species]))
        vx_render = tf.shade(vx_points, how='log')
        ray_vx = tf.spread(vx_render, px=3, shape='circle')

        ax.imshow(np.rot90(x_vx_phase.to_pil()))
        ax.imshow(np.rot90(ray_vx.to_pil()))

        ax.set_xlim(0, 300)
        ax.set_ylim(0, 800)

    phase_cmap, metal_cmap = cmaps.create_foggie_cmap()

    temp_colormap = phase_cmap
    ax6.imshow(np.rot90(temp_colormap.to_pil()))
    ax6.set_xlim(60, 180)
    ax6.set_ylim(0, 900)

    metal_colormap = metal_cmap
    ax7.imshow(np.rot90(metal_colormap.to_pil()))
    ax7.set_xlim(60, 180)
    ax7.set_ylim(0, 900)

    nh1 = np.sum(np.array(ray_df['dx'] * ray_df['H_p0_number_density']))
    nsi2 = np.sum(np.array(ray_df['dx'] * ray_df['Si_p1_number_density']))
    nc4 = np.sum(np.array(ray_df['dx'] * ray_df['C_p3_number_density']))
    no6 = np.sum(np.array(ray_df['dx'] * ray_df['O_p5_number_density']))

    comoving_box_size = ds.get_parameter('CosmologyComovingBoxSize') \
        / ds.get_parameter('CosmologyHubbleConstantNow') * 1000.

    x_ray = (ray_df[axis_to_use]-ray_start[ray_index]) * comoving_box_size * \
        ds.get_parameter('CosmologyHubbleConstantNow')  # comoving kpc
    ray_df['x_ray'] = x_ray[np.argsort(x_ray)]

    ray_length = ds.get_parameter('CosmologyHubbleConstantNow') * \
        comoving_box_size * \
        (ray_end[ray_index] - ray_start[ray_index])

    # Add the ionization fraction traces to the datashaded velocity vs. x plots
    h1 = np.array(50. * ray_df['H_p0_number_density'] /
                  np.max(ray_df['H_p0_number_density']))
    si2 = np.array(50. * ray_df['Si_p1_number_density'] / \
        np.max(ray_df['Si_p1_number_density']))
    c4 = np.array(50. * ray_df['C_p3_number_density'] / \
        np.max(ray_df['C_p3_number_density']))
    o6 = np.array(50. * ray_df['O_p5_number_density'] / \
        np.max(ray_df['O_p5_number_density']))
    ax2.step(h1, 800. - 4. * x_ray, linewidth=0.5)
    ax3.step(si2, 800. - 4. * x_ray, linewidth=0.5)
    ax4.step(c4, 800. - 4. * x_ray, linewidth=0.5)
    ax5.step(o6, 800. - 4. * x_ray, linewidth=0.5)

    # this will "histogram" the ions so we can plot them
    vxhist, h1hist = clouds.reduce_ion_vector(-1.*ray_df['x-velocity'], h1)
    vxhist, si2hist = clouds.reduce_ion_vector(-1.*ray_df['x-velocity'], si2)
    vxhist, c4hist = clouds.reduce_ion_vector(-1.*ray_df['x-velocity'], c4)
    vxhist, o6hist = clouds.reduce_ion_vector(-1.*ray_df['x-velocity'], o6)

    x = np.array(ray_length - x_ray)
    cell_mass = np.array(ray_df['cell_mass'])

    h1_size_dict = clouds.get_sizes(ray_df, 'h1', x, axis_to_use, np.array(
        ray_df['H_p0_number_density']), cell_mass, 0.8)
    for xx, ss in zip(h1_size_dict['h1_xs'], h1_size_dict['h1_kpcsizes']):
        ax2.plot([50., 50.], [4. * xx, 4. * (xx+ss)], '-')
    h1_size_dict['nh1'] = nh1

    si2_size_dict = clouds.get_sizes(ray_df, 'si2', x, axis_to_use, np.array(
        ray_df['Si_p1_number_density']), cell_mass, 0.8)
    for xx, ss in zip(si2_size_dict['si2_xs'], si2_size_dict['si2_kpcsizes']):
        ax3.plot([50., 50.], [4. * xx, 4. * (xx+ss)], '-')
    si2_size_dict['nsi2'] = nsi2

    c4_size_dict = clouds.get_sizes(ray_df, 'c4', x, axis_to_use, np.array(
        ray_df['C_p3_number_density']), cell_mass, 0.8)
    for xx, ss in zip(c4_size_dict['c4_xs'], c4_size_dict['c4_kpcsizes']):
        ax4.plot([50., 50.], [4. * xx, 4. * (xx+ss)], '-')
    c4_size_dict['nc4'] = nc4

    o6_size_dict = clouds.get_sizes(ray_df, 'o6', x, axis_to_use, np.array(
        ray_df['O_p5_number_density']), cell_mass, 0.8)
    for xx, ss in zip(o6_size_dict['o6_xs'], o6_size_dict['o6_kpcsizes']):
        ax5.plot([50., 50.], [4. * xx, 4. * (xx+ss)], '-')
    o6_size_dict['no6'] = no6

    size_dict = {**h1_size_dict, **si2_size_dict,  # concatenate the dicts
                 **c4_size_dict, **o6_size_dict}
    pickle.dump(size_dict, open(fileroot+"sizes.pkl", "wb"))

    for ax, key in zip([ax8, ax9, ax10, ax11],
                       ['H I 1216', 'Si II 1260', 'C IV 1548', 'O VI 1032']):
        ax.set_xlim(-350, 350)
        ax.set_ylim(0, 1)
        ax.set_yticklabels([' ', ' ', ' '])
        if (hdulist.__contains__(key)):
            restwave = hdulist[key].header['RESTWAVE'] * u.AA
            with u.set_enabled_equivalencies(
                    u.equivalencies.doppler_relativistic(restwave)):
                vel = (hdulist[key].data['wavelength']*u.AA /
                       (1 + ds.get_parameter('CosmologyCurrentRedshift'))).to('km/s')
            ax.step(vel, hdulist[key].data['flux'])

    for v in np.flip(h1_size_dict['h1_velocities'], 0):
        ax8.plot(-1.*v, np.array(v)*0.0 + 0.1, '|')

    for v in np.flip(si2_size_dict['si2_velocities'], 0):
        ax9.plot(-1.*v, np.array(v)*0.0 + 0.1, '|')

    for v in np.flip(c4_size_dict['c4_velocities'], 0):
        ax10.plot(-1.*v, np.array(v)*0.0 + 0.1, '|')

    for v in np.flip(o6_size_dict['o6_velocities'], 0):
        ax11.plot(-1.*v, np.array(v)*0.0 + 0.1, '|')

    for ax in [ax2, ax3, ax4, ax5, ax6, ax7]:
        ax.axes.get_xaxis().set_ticks([])
        ax.axes.get_yaxis().set_ticks([])

    ax6.set_yticks([0, 400, 800])
    ax6.set_yticklabels(['4', '5', '6'], fontname='Arial', fontsize=7)
    ax6.set_xlabel('log T', fontname='Arial', fontsize=8)

    ax7.set_yticks([0, 400, 800])
    ax7.set_yticklabels(['-4', '-2', '0'],
                        fontname='Arial', fontsize=7)
    ax7.set_xlabel('log Z', fontname='Arial', fontsize=8)

    ax1.set_yticks([])
    ax0.set_xticks([])
    ax1.set_xticks([])
    ax0.set_xlim(60, 140)
    ax1.set_xlim(60, 140)

    gs.update(hspace=0.0, wspace=0.1)
    plt.savefig(fileroot+'velphase.png', dpi=300)
    plt.close(fig)



def grab_ray_file(ds, filename):
    """
    opens a fits file containing a FOGGIE / Trident ray and returns a dataframe
    with useful quantities along the ray
    """
    print("grab_ray_file is opening: ", filename)
    hdulist = fits.open(filename)
    ray_start_str = hdulist[0].header['RAYSTART']
    ray_end_str = hdulist[0].header['RAYEND']
    ray_start = [float(ray_start_str.split(",")[0].strip('unitary')),
                 float(ray_start_str.split(",")[1].strip('unitary')),
                 float(ray_start_str.split(",")[2].strip('unitary'))]
    ray_end = [float(ray_end_str.split(",")[0].strip('unitary')),
               float(ray_end_str.split(",")[1].strip('unitary')),
               float(ray_end_str.split(",")[2].strip('unitary'))]
    rs, re = np.array(ray_start), np.array(ray_end)
    rs = ds.arr(rs, "code_length")
    re = ds.arr(re, "code_length")
    ray = ds.ray(rs, re)
    rs = rs.ndarray_view()
    re = re.ndarray_view()
    ray['x-velocity'] = ray['x-velocity'].convert_to_units('km/s')
    ray['y-velocity'] = ray['y-velocity'].convert_to_units('km/s')
    ray['z-velocity'] = ray['z-velocity'].convert_to_units('km/s')
    ray['dx'] = ray['dx'].convert_to_units('cm')

    ray_df = ray.to_dataframe(["x", "y", "z", "density", "temperature",
                               "metallicity", "HI_Density", "cell_mass", "dx",
                               "x-velocity", "y-velocity", "z-velocity",
                               "C_p2_number_density", "C_p3_number_density",
                               "H_p0_number_density", "Mg_p1_number_density",
                               "O_p5_number_density", "Si_p2_number_density",
                               "Si_p1_number_density", "Si_p3_number_density",
                               "Ne_p7_number_density"])

    ray_index, first_axis, second_axis = futils.get_ray_axis(rs, re)

    ray_df = ray_df.sort_values(by=[first_axis])

    return ray_df, rs, re, first_axis, hdulist

def loop_over_rays(ds, dataset_list):
    for filename in dataset_list:
        ray_df, rs, re, axis_to_use, hdulist = grab_ray_file(
            ds, filename)
        show_velphase(ds, ray_df, rs, re, hdulist,
                      filename.strip('los.fits.gz'))

def drive_velphase(ds_name, wildcard):
    """
    for running as imported module.
    """
    ds = yt.load(ds_name)
    trident.add_ion_fields(ds, ions=['Si II', 'Si III', 'Si IV', 'C II',
                                     'C III', 'C IV', 'O VI', 'Mg II',
                                     'Ne VIII'])

    dataset_list = glob.glob(os.path.join(os.getcwd(), wildcard))
    loop_over_rays(ds, dataset_list)

if __name__ == "__main__":
    """
    for running at the command line.
    """
    args = futils.parse_args()
    ds_loc, output_path, output_dir, haloname = futils.get_path_info(
        args)

    dataset_list = glob.glob(
        os.path.join('.', '*rd0020*v6_los*fits.gz'))
    print('there are ', len(dataset_list), 'files')

    ds = yt.load(ds_loc)
    trident.add_ion_fields(ds, ions=['Si II', 'Si III', 'Si IV', 'C II',
                                     'C III', 'C IV', 'O VI', 'Mg II',
                                     'Ne VIII'])

    print('going to loop over rays now')
    loop_over_rays(ds, dataset_list)
    print('~~~ all done! ~~~')
