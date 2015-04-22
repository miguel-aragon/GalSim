# Copyright (c) 2012-2015 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#
import numpy as np
import os
import sys

from galsim_test_helpers import *

"""Unit tests for the InterpolatedImage class.
"""

path, filename = os.path.split(__file__) # Get the path to this file for use below...
try:
    import galsim
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

# for flux normalization tests
test_flux = 0.7
# for scale tests - avoid 1.0 because factors of scale^2 won't show up!
test_scale = 2.0

# For reference tests:
TESTDIR=os.path.join(path, "interpolant_comparison_files")

# Some arbitrary kx, ky k space values to test
KXVALS = np.array((1.30, 0.71, -4.30)) * np.pi / 2.
KYVALS = np.array((0.80, -0.02, -0.31,)) * np.pi / 2.

# First make an image that we'll use for interpolation:
g1 = galsim.Gaussian(sigma = 3.1, flux=2.4).shear(g1=0.2,g2=0.1)
g2 = galsim.Gaussian(sigma = 1.9, flux=3.1).shear(g1=-0.4,g2=0.3).shift(-0.3,0.5)
g3 = galsim.Gaussian(sigma = 4.1, flux=1.6).shear(g1=0.1,g2=-0.1).shift(0.7,-0.2)

final = g1 + g2 + g3
ref_image = galsim.ImageD(128,128)
scale = 0.4
# The reference image was drawn with the old convention, which is now use_true_center=False
final.drawImage(image=ref_image, scale=scale, method='sb', use_true_center=False)

def test_roundtrip():
    """Test round trip from Image to InterpolatedImage back to Image.
    """
    import time
    t1 = time.time()

    # for each type, try to make an InterpolatedImage, and check that when we draw an image from
    # that InterpolatedImage that it is the same as the original
    ftypes = [np.float32, np.float64]
    ref_array = np.array([
        [0.01, 0.08, 0.07, 0.02],
        [0.13, 0.38, 0.52, 0.06],
        [0.09, 0.41, 0.44, 0.09],
        [0.04, 0.11, 0.10, 0.01] ]) 

    for array_type in ftypes:
        image_in = galsim.Image(ref_array.astype(array_type))
        np.testing.assert_array_equal(
                ref_array.astype(array_type),image_in.array,
                err_msg="Array from input Image differs from reference array for type %s"%
                        array_type)
        interp = galsim.InterpolatedImage(image_in, scale=test_scale)
        test_array = np.zeros(ref_array.shape, dtype=array_type)
        image_out = galsim.Image(test_array, scale=test_scale)
        interp.drawImage(image_out, method='no_pixel')
        np.testing.assert_array_equal(
                ref_array.astype(array_type),image_out.array,
                err_msg="Array from output Image differs from reference array for type %s"%
                        array_type)

        # Lanczos doesn't quite get the flux right.  Wrong at the 5th decimal place.
        # Gary says that's expected -- Lanczos isn't technically flux conserving.  
        # He applied the 1st order correction to the flux, but expect to be wrong at around
        # the 10^-5 level.
        # Anyway, Quintic seems to be accurate enough.
        # And this is now the default, so no need to do anything special here.
        do_shoot(interp,image_out,"InterpolatedImage")

        # Test kvalues
        test_im = galsim.Image(16,16,scale=0.2)
        do_kvalue(interp,test_im,"InterpolatedImage")

        # Check picklability
        do_pickle(interp._sbii, lambda x: (galsim.Image(x.getImage()), x.stepK(), x.maxK()))
        do_pickle(interp.SBProfile, lambda x: repr(x))
        do_pickle(interp, lambda x: x.drawImage(method='no_pixel'))
        do_pickle(interp)
        do_pickle(interp.SBProfile)

    # Also check picklability of the Interpolants
    im = galsim.Gaussian(sigma=4).drawImage()
    test_func = lambda x : (
        galsim.InterpolatedImage(im, x_interpolant=x).drawImage(method='no_pixel'))

    do_pickle(galsim.Delta(), test_func)
    do_pickle(galsim.Delta(tol=0.1), test_func)
    do_pickle(galsim.Delta())
    do_pickle(galsim.Nearest(), test_func)
    do_pickle(galsim.Nearest(tol=0.1), test_func)
    do_pickle(galsim.Nearest())
    do_pickle(galsim.SincInterpolant(tol=0.1), test_func)  # Can't really do this with tol=1.e-4
    do_pickle(galsim.SincInterpolant())
    do_pickle(galsim.Linear(), test_func)
    do_pickle(galsim.Linear(tol=0.1), test_func)
    do_pickle(galsim.Linear())
    do_pickle(galsim.Lanczos(3), test_func)
    do_pickle(galsim.Lanczos(n=7, conserve_dc=False, tol=0.1), test_func)
    do_pickle(galsim.Lanczos(3))
    do_pickle(galsim.Cubic(), test_func)
    do_pickle(galsim.Cubic(tol=0.1), test_func)
    do_pickle(galsim.Cubic())
    do_pickle(galsim.Quintic(), test_func)
    do_pickle(galsim.Quintic(tol=0.1), test_func)
    do_pickle(galsim.Quintic())
    do_pickle(galsim.Interpolant('quintic'), test_func)
    do_pickle(galsim.Interpolant('lanczos7'), test_func)
    do_pickle(galsim.Interpolant('lanczos9F'), test_func)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_fluxnorm():
    """Test that InterpolatedImage class responds properly to instructions about flux normalization.
    """
    import time
    t1 = time.time()

    # define values
    # Note that im_lin_scale should be even, since the auto-sized drawImage() command always
    # produces an even-sized image.  If the even/odd-ness doesn't match then the interpolant will
    # come into play, and the exact checks will fail.
    im_lin_scale = 6 # make an image with this linear scale
    im_fill_value = 3. # fill it with this number
    im_scale = 1.3

    # First, make some Image with some total flux value (sum of pixel values) and scale
    im = galsim.ImageF(im_lin_scale, im_lin_scale, scale=im_scale, init_value=im_fill_value)
    total_flux = im_fill_value*(im_lin_scale**2)
    np.testing.assert_equal(total_flux, im.array.sum(),
                            err_msg='Created array with wrong total flux')

    # Check that if we make an InterpolatedImage with flux normalization, it keeps that flux
    interp = galsim.InterpolatedImage(im) # note, flux normalization is the default
    np.testing.assert_almost_equal(total_flux, interp.getFlux(), decimal=9,
                            err_msg='Did not keep flux normalization')
    # Check that this is preserved when drawing
    im2 = interp.drawImage(scale = im_scale, method='no_pixel')
    np.testing.assert_almost_equal(total_flux, im2.array.sum(), decimal=9,
                                   err_msg='Drawn image does not have expected flux normalization')
    do_pickle(interp, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(interp)

    # Now make an InterpolatedImage but tell it sb normalization
    interp_sb = galsim.InterpolatedImage(im, normalization = 'sb')
    # Check that when drawing, the sum is equal to what we expect if the original image had been
    # surface brightness
    im3 = interp_sb.drawImage(scale = im_scale, method='no_pixel')
    np.testing.assert_almost_equal(total_flux*(im_scale**2)/im3.array.sum(), 1.0, decimal=6,
                                   err_msg='Did not use surface brightness normalization')
    # Check that when drawing with sb normalization, the sum is the same as the original
    im4 = interp_sb.drawImage(scale = im_scale, method='sb')
    np.testing.assert_almost_equal(total_flux/im4.array.sum(), 1.0, decimal=6,
                                   err_msg='Failed roundtrip for sb normalization')
    do_pickle(interp_sb, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(interp_sb)

    # Finally make an InterpolatedImage but give it some other flux value
    interp_flux = galsim.InterpolatedImage(im, flux=test_flux)
    # Check that it has that flux
    np.testing.assert_equal(test_flux, interp_flux.getFlux(),
                            err_msg = 'InterpolatedImage did not use flux keyword')
    # Check that this is preserved when drawing
    im5 = interp_flux.drawImage(scale = im_scale, method='no_pixel')
    np.testing.assert_almost_equal(test_flux/im5.array.sum(), 1.0, decimal=6,
                                   err_msg = 'Drawn image does not reflect flux keyword')
    do_pickle(interp_flux, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(interp_flux)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_exceptions():
    """Test failure modes for InterpolatedImage class.
    """
    import time
    t1 = time.time()

    try:
        # What if it receives as input something that is not an Image? Give it a GSObject to check.
        g = galsim.Gaussian(sigma=1.)
        np.testing.assert_raises(ValueError, galsim.InterpolatedImage, g)
        # What if Image does not have a scale set, but scale keyword is not specified?
        im = galsim.ImageF(5, 5)
        np.testing.assert_raises(ValueError, galsim.InterpolatedImage, im)
        # Image must have bounds defined
        im = galsim.ImageF()
        im.scale = 1.
        np.testing.assert_raises(ValueError, galsim.InterpolatedImage, im)
        # Weird flux normalization
        im = galsim.ImageF(5, 5, scale=1.)
        np.testing.assert_raises(ValueError, galsim.InterpolatedImage, im, normalization = 'foo')
        # scale and WCS
        np.testing.assert_raises(TypeError, galsim.InterpolatedImage, im,
                                 wcs = galsim.PixelScale(1.), scale=1.)
        # weird WCS
        np.testing.assert_raises(TypeError, galsim.InterpolatedImage, im,
                                 wcs = 1.)
        # Weird interpolant - give it something random like a GSObject
        np.testing.assert_raises(Exception, galsim.InterpolatedImage, im, x_interpolant = g)
        # Image has wrong type
        im = galsim.ImageI(5, 5)
        np.testing.assert_raises(ValueError, galsim.InterpolatedImage, im)
    except ImportError:
        print 'The assert_raises tests require nose'

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_operations_simple():
    """Simple test of operations on InterpolatedImage: shear, magnification, rotation, shifting."""
    import time
    t1 = time.time()

    # Make some nontrivial image that can be described in terms of sums and convolutions of
    # GSObjects.  We want this to be somewhat hard to describe, but should be at least
    # critically-sampled, so put in an Airy PSF.
    gal_flux = 1000.
    pix_scale = 0.03 # arcsec
    bulge_frac = 0.3
    bulge_hlr = 0.3 # arcsec
    bulge_e = 0.15
    bulge_pos_angle = 30.*galsim.degrees
    disk_hlr = 0.6 # arcsec
    disk_e = 0.5
    disk_pos_angle = 60.*galsim.degrees
    lam = 800              # nm    NB: don't use lambda - that's a reserved word.
    tel_diam = 2.4         # meters
    lam_over_diam = lam * 1.e-9 / tel_diam # radians
    lam_over_diam *= 206265  # arcsec
    im_size = 512

    # define subregion for comparison
    comp_region=30 # compare the central region of this linear size
    comp_bounds = galsim.BoundsI(1,comp_region,1,comp_region)
    comp_bounds = comp_bounds.shift(galsim.PositionI((im_size-comp_region)/2,
                                                     (im_size-comp_region)/2))

    bulge = galsim.Sersic(4, half_light_radius=bulge_hlr)
    bulge = bulge.shear(e=bulge_e, beta=bulge_pos_angle)
    disk = galsim.Exponential(half_light_radius = disk_hlr)
    disk = disk.shear(e=disk_e, beta=disk_pos_angle)
    gal = bulge_frac*bulge + (1.-bulge_frac)*disk
    gal = gal.withFlux(gal_flux)
    psf = galsim.Airy(lam_over_diam)
    obj = galsim.Convolve([gal, psf])
    im = obj.drawImage(scale=pix_scale)

    # Turn it into an InterpolatedImage with default param settings
    int_im = galsim.InterpolatedImage(im)

    # Shear it, and compare with expectations from GSObjects directly
    test_g1=-0.07
    test_g2=0.1
    test_decimal=2 # in % difference, i.e. 2 means 1% agreement
    test_int_im = int_im.shear(g1=test_g1, g2=test_g2)
    ref_obj = obj.shear(g1=test_g1, g2=test_g2)
    # make large images
    im = galsim.ImageD(im_size, im_size)
    ref_im = galsim.ImageD(im_size, im_size)
    test_int_im.drawImage(image=im, scale=pix_scale, method='no_pixel')
    ref_obj.drawImage(image=ref_im, scale=pix_scale)
    # define subregion for comparison
    im_sub = im.subImage(comp_bounds)
    ref_im_sub = ref_im.subImage(comp_bounds)
    diff_im=im_sub-ref_im_sub
    rel = diff_im/im_sub
    zeros_arr = np.zeros((comp_region, comp_region))
    # require relative difference to be smaller than some amount
    np.testing.assert_array_almost_equal(rel.array, zeros_arr,
        test_decimal,
        err_msg='Sheared InterpolatedImage disagrees with reference')
    if __name__ == "__main__":
        do_pickle(test_int_im, lambda x: x.drawImage(nx=5, ny=5, scale=0.1, method='no_pixel'))
        do_pickle(test_int_im)

    # Magnify it, and compare with expectations from GSObjects directly
    test_mag = 1.08
    test_decimal=2 # in % difference, i.e. 2 means 1% agreement
    comp_region=30 # compare the central region of this linear size
    test_int_im = int_im.magnify(test_mag)
    ref_obj = obj.magnify(test_mag)
    # make large images
    im = galsim.ImageD(im_size, im_size)
    ref_im = galsim.ImageD(im_size, im_size)
    test_int_im.drawImage(image=im, scale=pix_scale, method='no_pixel')
    ref_obj.drawImage(image=ref_im, scale=pix_scale)
    # define subregion for comparison
    im_sub = im.subImage(comp_bounds)
    ref_im_sub = ref_im.subImage(comp_bounds)
    diff_im=im_sub-ref_im_sub
    rel = diff_im/im_sub
    zeros_arr = np.zeros((comp_region, comp_region))
    # require relative difference to be smaller than some amount
    np.testing.assert_array_almost_equal(rel.array, zeros_arr,
        test_decimal,
        err_msg='Magnified InterpolatedImage disagrees with reference')
    if __name__ == "__main__":
        do_pickle(test_int_im, lambda x: x.drawImage(nx=5, ny=5, scale=0.1, method='no_pixel'))
        do_pickle(test_int_im)

    # Lens it (shear and magnify), and compare with expectations from GSObjects directly
    test_g1 = -0.03
    test_g2 = -0.04
    test_mag = 0.74
    test_decimal=2 # in % difference, i.e. 2 means 1% agreement
    comp_region=30 # compare the central region of this linear size
    test_int_im = int_im.lens(test_g1, test_g2, test_mag)
    ref_obj = obj.lens(test_g1, test_g2, test_mag)
    # make large images
    im = galsim.ImageD(im_size, im_size)
    ref_im = galsim.ImageD(im_size, im_size)
    test_int_im.drawImage(image=im, scale=pix_scale, method='no_pixel')
    ref_obj.drawImage(image=ref_im, scale=pix_scale)
    # define subregion for comparison
    im_sub = im.subImage(comp_bounds)
    ref_im_sub = ref_im.subImage(comp_bounds)
    diff_im=im_sub-ref_im_sub
    rel = diff_im/im_sub
    zeros_arr = np.zeros((comp_region, comp_region))
    # require relative difference to be smaller than some amount
    np.testing.assert_array_almost_equal(rel.array, zeros_arr,
        test_decimal,
        err_msg='Lensed InterpolatedImage disagrees with reference')
    if __name__ == "__main__":
        do_pickle(test_int_im, lambda x: x.drawImage(nx=5, ny=5, scale=0.1, method='no_pixel'))
        do_pickle(test_int_im)

    # Rotate it, and compare with expectations from GSObjects directly
    test_rot_angle = 32.*galsim.degrees
    test_decimal=2 # in % difference, i.e. 2 means 1% agreement
    comp_region=30 # compare the central region of this linear size
    test_int_im = int_im.rotate(test_rot_angle)
    ref_obj = obj.rotate(test_rot_angle)
    # make large images
    im = galsim.ImageD(im_size, im_size)
    ref_im = galsim.ImageD(im_size, im_size)
    test_int_im.drawImage(image=im, scale=pix_scale, method='no_pixel')
    ref_obj.drawImage(image=ref_im, scale=pix_scale)
    # define subregion for comparison
    im_sub = im.subImage(comp_bounds)
    ref_im_sub = ref_im.subImage(comp_bounds)
    diff_im=im_sub-ref_im_sub
    rel = diff_im/im_sub
    zeros_arr = np.zeros((comp_region, comp_region))
    # require relative difference to be smaller than some amount
    np.testing.assert_array_almost_equal(rel.array, zeros_arr,
        test_decimal,
        err_msg='Rotated InterpolatedImage disagrees with reference')
    if __name__ == "__main__":
        do_pickle(test_int_im, lambda x: x.drawImage(nx=5, ny=5, scale=0.1, method='no_pixel'))
        do_pickle(test_int_im)

    # Shift it, and compare with expectations from GSObjects directly
    x_shift = -0.31
    y_shift = 0.87
    test_decimal=2 # in % difference, i.e. 2 means 1% agreement
    comp_region=30 # compare the central region of this linear size
    test_int_im = int_im.shift(x_shift, y_shift)
    ref_obj = obj.shift(x_shift, y_shift)
    # make large images
    im = galsim.ImageD(im_size, im_size)
    ref_im = galsim.ImageD(im_size, im_size)
    test_int_im.drawImage(image=im, scale=pix_scale, method='no_pixel')
    ref_obj.drawImage(image=ref_im, scale=pix_scale)
    # define subregion for comparison
    im_sub = im.subImage(comp_bounds)
    ref_im_sub = ref_im.subImage(comp_bounds)
    diff_im=im_sub-ref_im_sub
    rel = diff_im/im_sub
    zeros_arr = np.zeros((comp_region, comp_region))
    # require relative difference to be smaller than some amount
    np.testing.assert_array_almost_equal(rel.array, zeros_arr,
        test_decimal,
        err_msg='Shifted InterpolatedImage disagrees with reference')
    if __name__ == "__main__":
        do_pickle(test_int_im, lambda x: x.drawImage(nx=5, ny=5, scale=0.1, method='no_pixel'))
        do_pickle(test_int_im)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_operations():
    """Test of operations on complicated InterpolatedImage: shear, magnification, rotation,
    shifting.
    """
    import time
    t1 = time.time()
    test_decimal = 3

    # Make some nontrivial image
    im = galsim.fits.read('./real_comparison_images/test_images.fits') # read in first real galaxy
                                                                       # in test catalog
    int_im = galsim.InterpolatedImage(im)
    orig_mom = im.FindAdaptiveMom()

    # Magnify by some amount and make sure change is as expected
    mu = 0.92
    new_int_im = int_im.magnify(mu)
    test_im = galsim.ImageF(im.bounds)
    new_int_im.drawImage(image = test_im, scale = im.scale, method='no_pixel')
    new_mom = test_im.FindAdaptiveMom()
    np.testing.assert_almost_equal(new_mom.moments_sigma/np.sqrt(mu),
        orig_mom.moments_sigma, test_decimal,
        err_msg = 'Size of magnified InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.observed_shape.e1, orig_mom.observed_shape.e1,
        test_decimal,
        err_msg = 'e1 of magnified InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.observed_shape.e2, orig_mom.observed_shape.e2,
        test_decimal,
        err_msg = 'e2 of magnified InterpolatedImage from HST disagrees with expectations')
    do_pickle(new_int_im, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(new_int_im)

    # Shift, make sure change in moments is as expected
    x_shift = 0.92
    y_shift = -0.16
    new_int_im = int_im.shift(x_shift, y_shift)
    test_im = galsim.ImageF(im.bounds)
    new_int_im.drawImage(image = test_im, scale = im.scale, method='no_pixel')
    new_mom = test_im.FindAdaptiveMom()
    np.testing.assert_almost_equal(new_mom.moments_sigma, orig_mom.moments_sigma,
        test_decimal,
        err_msg = 'Size of shifted InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.moments_centroid.x-x_shift, orig_mom.moments_centroid.x,
        test_decimal,
        err_msg = 'x centroid of shifted InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.moments_centroid.y-y_shift, orig_mom.moments_centroid.y,
        test_decimal,
        err_msg = 'y centroid of shifted InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.observed_shape.e1, orig_mom.observed_shape.e1,
        test_decimal,
        err_msg = 'e1 of shifted InterpolatedImage from HST disagrees with expectations')
    np.testing.assert_almost_equal(new_mom.observed_shape.e2, orig_mom.observed_shape.e2,
        test_decimal,
        err_msg = 'e2 of shifted InterpolatedImage from HST disagrees with expectations')
    do_pickle(new_int_im, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(new_int_im)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_uncorr_padding():
    """Test for uncorrelated noise padding of InterpolatedImage."""
    import time
    t1 = time.time()

    # Set up some defaults: use weird image sizes / shapes and noise variances.
    decimal_precise=5
    decimal_coarse=2
    orig_nx = 147
    orig_ny = 174
    noise_var = 1.73
    big_nx = 519
    big_ny = 482
    orig_seed = 151241

    # first, make a noise image
    orig_img = galsim.ImageF(orig_nx, orig_ny, scale=1.)
    gd = galsim.GaussianDeviate(orig_seed, mean=0., sigma=np.sqrt(noise_var))
    orig_img.addNoise(galsim.DeviateNoise(gd))

    # make it into an InterpolatedImage with some zero-padding
    # (note that default is zero-padding, by factors of several)
    int_im = galsim.InterpolatedImage(orig_img)
    # draw into a larger image
    big_img = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img, scale=1., method='no_pixel')
    # check that variance is diluted by expected amount - should be exact, so check precisely!
    # Note that this only works if the big image has the same even/odd-ness in the two sizes.
    # Otherwise the center of the original image will fall between pixels in the big image.
    # Then the variance will be smoothed somewhat by the interpolant.
    big_var_expected = np.var(orig_img.array)*float(orig_nx*orig_ny)/(big_nx*big_ny)
    np.testing.assert_almost_equal(
        np.var(big_img.array), big_var_expected, decimal=decimal_precise,
        err_msg='Variance not diluted by expected amount when zero-padding')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # make it into an InterpolatedImage with noise-padding
    int_im = galsim.InterpolatedImage(orig_img, noise_pad=noise_var,
                                      noise_pad_size=max(big_nx,big_ny),
                                      rng = galsim.GaussianDeviate(orig_seed))
    # draw into a larger image
    big_img = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img, scale=1., method='no_pixel')
    # check that variance is same as original - here, we cannot be too precise because the padded
    # region is not huge and the comparison will be, well, noisy.
    np.testing.assert_almost_equal(
        np.var(big_img.array), noise_var, decimal=decimal_coarse,
        err_msg='Variance not correct after padding image with noise')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # check that if we pass in a RNG, it is actually used to pad with the same noise field
    # basically, redo all of the above steps and draw into a new image, make sure it's the same as
    # previous.
    int_im = galsim.InterpolatedImage(orig_img, noise_pad=noise_var,
                                      noise_pad_size=max(big_nx,big_ny),
                                      rng = galsim.GaussianDeviate(orig_seed))
    big_img_2 = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img_2, scale=1., method='no_pixel')
    np.testing.assert_array_almost_equal(
        big_img_2.array, big_img.array, decimal=decimal_precise,
        err_msg='Cannot reproduce noise-padded image with same choice of seed')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # Finally check inputs: what if we give it an input variance that is neg?  A list?
    try:
        np.testing.assert_raises(ValueError,galsim.InterpolatedImage,orig_img,noise_pad=-1.)
    except ImportError:
        print 'The assert_raises tests require nose'

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_pad_image():
    """Test padding an InterpolatedImage with a pad_image."""
    import time
    t1 = time.time()

    decimal=2  # all are coarse, since there are slight changes from odd/even centering issues.
    noise_sigma = 1.73
    noise_var = noise_sigma**2
    orig_seed = 12345
    rng = galsim.BaseDeviate(orig_seed)
    noise = galsim.GaussianNoise(rng, sigma=noise_sigma)

    # make the original image 
    orig_nx = 64
    orig_ny = 64
    orig_img = galsim.ImageF(orig_nx, orig_ny, scale=1.)
    galsim.Exponential(scale_radius=1.7,flux=1000).drawImage(orig_img, method='no_pixel')
    orig_img.addNoise(noise)
    orig_img.setCenter(0,0)

    # We'll draw into a larger image for the tests
    pad_factor = 4
    big_nx = pad_factor*orig_nx
    big_ny = pad_factor*orig_ny
    big_img = galsim.ImageF(big_nx, big_ny, scale=1.)
    big_img.setCenter(0,0)

    # Use a few different kinds of shapes for that padding. 
    for (pad_nx, pad_ny) in [ (160,160), (179,191), (256,256), (305, 307) ]:
        #print 'pad size = ',pad_nx, pad_ny

        # make the pad_image 
        pad_img = galsim.ImageF(pad_nx, pad_ny, scale=1.)
        pad_img.addNoise(noise)
        pad_img.setCenter(0,0)

        # make an interpolated image padded with the pad_image, and outside of that
        int_im = galsim.InterpolatedImage(orig_img, pad_image=pad_img, use_true_center=False)

        # draw into the larger image
        int_im.drawImage(big_img, use_true_center=False, method='no_pixel')

        # check that variance is diluted by expected amount 
        # Note -- we don't use np.var, since that computes the variance relative to the 
        # actual mean value.  We just want sum(I^2)/Npix relative to the nominal I=0 value.
        var1 = np.sum(orig_img.array**2)
        if pad_nx > big_nx and pad_ny > big_ny:
            var2 = np.sum(pad_img[big_img.bounds].array**2)
        else:
            var2 = np.sum(pad_img.array**2) 
        var2 -= np.sum(pad_img[orig_img.bounds].array**2)
        var_expected = (var1 + var2) / (big_nx*big_ny)
        big_img.setCenter(0,0)
        np.testing.assert_almost_equal(
            np.mean(big_img.array**2), var_expected, decimal=decimal,
            err_msg='Variance not correct when padding with image')
        if __name__ == '__main__':
            do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
            do_pickle(int_im)

        if pad_nx < big_nx and pad_ny < big_ny:
            # now also pad with noise_pad outside of the pad_image
            int_im = galsim.InterpolatedImage(orig_img, pad_image=pad_img, noise_pad=noise_var/2,
                                              noise_pad_size=max(big_nx,big_ny),
                                              rng=rng, use_true_center=False)
            int_im.drawImage(big_img, use_true_center=False, method='no_pixel')
    
            var3 = (noise_var/2) * float(big_nx*big_ny - pad_nx*pad_ny)
            var_expected = (var1 + var2 + var3) / (big_nx*big_ny)
            np.testing.assert_almost_equal(
                np.mean(big_img.array**2), var_expected, decimal=decimal,
                err_msg='Variance not correct after padding with image and extra noise')
            if __name__ == '__main__':
                do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
                do_pickle(int_im)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_corr_padding():
    """Test for correlated noise padding of InterpolatedImage."""
    import time
    t1 = time.time()

    # Set up some defaults for tests.
    decimal_precise=4
    decimal_coarse=2
    imgfile = 'fits_files/blankimg.fits'
    orig_nx = 187
    orig_ny = 164
    big_nx = 319
    big_ny = 322
    orig_seed = 151241

    # Read in some small image of a noise field from HST.
    # Rescale it to have a decently large amplitude for the purpose of doing these tests.
    im = 1.e2*galsim.fits.read(imgfile)
    # Make a CorrrlatedNoise out of it.
    cn = galsim.CorrelatedNoise(im, galsim.BaseDeviate(orig_seed))

    # first, make a noise image
    orig_img = galsim.ImageF(orig_nx, orig_ny, scale=1.)
    orig_img.addNoise(cn)

    # make it into an InterpolatedImage with some zero-padding
    # (note that default is zero-padding, by factors of several)
    int_im = galsim.InterpolatedImage(orig_img)
    # draw into a larger image
    big_img = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img, scale=1., method='no_pixel')
    # check that variance is diluted by expected amount - should be exact, so check precisely!
    big_var_expected = np.var(orig_img.array)*float(orig_nx*orig_ny)/(big_nx*big_ny)
    np.testing.assert_almost_equal(np.var(big_img.array), big_var_expected, decimal=decimal_precise,
        err_msg='Variance not diluted by expected amount when zero-padding')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # make it into an InterpolatedImage with noise-padding
    int_im = galsim.InterpolatedImage(orig_img, rng = galsim.GaussianDeviate(orig_seed),
                                      noise_pad = im, noise_pad_size = max(big_nx,big_ny))

    # draw into a larger image
    big_img = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img, scale=1., method='no_pixel')
    # check that variance is same as original - here, we cannot be too precise because the padded
    # region is not huge and the comparison will be, well, noisy.
    np.testing.assert_almost_equal(np.var(big_img.array), np.var(orig_img.array),
        decimal=decimal_coarse,
        err_msg='Variance not correct after padding image with correlated noise')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # check that if we pass in a RNG, it is actually used to pad with the same noise field
    # basically, redo all of the above steps and draw into a new image, make sure it's the same as
    # previous.
    int_im = galsim.InterpolatedImage(
        orig_img, rng=galsim.GaussianDeviate(orig_seed), noise_pad=cn,
        noise_pad_size = max(big_nx,big_ny))
    big_img_2 = galsim.ImageF(big_nx, big_ny)
    int_im.drawImage(big_img_2, scale=1., method='no_pixel')
    np.testing.assert_array_almost_equal(big_img_2.array, big_img.array, decimal=decimal_precise,
        err_msg='Cannot reproduce correlated noise-padded image with same choice of seed')
    if __name__ == '__main__':
        do_pickle(int_im, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im)

    # Finally, check inputs:
    # what if we give it a screwy way of defining the image padding?
    try:
        np.testing.assert_raises(ValueError,galsim.InterpolatedImage,orig_img,noise_pad=-1.)
    except ImportError:
        print 'The assert_raises tests require nose'
    # also, check that whether we give it a string, image, or cn, it gives the same noise field
    # (given the same random seed)
    infile = 'fits_files/blankimg.fits'
    inimg = galsim.fits.read(infile)
    incf = galsim.CorrelatedNoise(inimg, galsim.GaussianDeviate()) # input RNG will be ignored below
    int_im2 = galsim.InterpolatedImage(orig_img, rng=galsim.GaussianDeviate(orig_seed),
                                       noise_pad=inimg, noise_pad_size = max(big_nx,big_ny))
    int_im3 = galsim.InterpolatedImage(orig_img, rng=galsim.GaussianDeviate(orig_seed),
                                       noise_pad=incf, noise_pad_size = max(big_nx,big_ny))
    big_img2 = galsim.ImageF(big_nx, big_ny)
    big_img3 = galsim.ImageF(big_nx, big_ny)
    int_im2.drawImage(big_img2, scale=1., method='no_pixel')
    int_im3.drawImage(big_img3, scale=1., method='no_pixel')
    np.testing.assert_equal(big_img2.array, big_img3.array,
                            err_msg='Diff ways of specifying correlated noise give diff answers')
    if __name__ == '__main__':
        do_pickle(int_im2, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im3, lambda x: x.drawImage(nx=200, ny=200, scale=1, method='no_pixel'))
        do_pickle(int_im2)
        do_pickle(int_im3)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_realspace_conv():
    """Test that real-space convolution of an InterpolatedImage matches the FFT result
    """
    import time
    t1 = time.time()

    # Note: It is not usually a good idea to use real-space convolution with an InterpolatedImage.
    # It will almost always be much slower than the FFT convolution.  So it's probably only
    # a good idea if the image is very small and/or you absolutely need to avoid the ringing
    # that can show up in FFT convolutions.
    # That said, we still need to make sure the code is correct.  Especially since it 
    # didn't used to be, as reported in issue #432.  So, here goes.

    # set up image scale and size
    raw_scale = 0.23
    raw_size = 15

    # We draw onto a smaller image so the unit test doesn't take forever!
    target_scale = 0.7
    target_size = 3 

    gal = galsim.Exponential(flux=1.7, half_light_radius=1.2)
    gal_im = gal.drawImage(scale=raw_scale, nx=raw_size, ny=raw_size, method='no_pixel')

    psf1 = galsim.Gaussian(flux=1, half_light_radius=0.77)
    psf_im = psf1.drawImage(scale=raw_scale, nx=raw_size, ny=raw_size, method='no_pixel')

    if __name__ == "__main__":
        interp_list = ['linear', 'cubic', 'quintic', 'lanczos3', 'lanczos5', 'lanczos7']
    else:
        interp_list = ['linear', 'cubic', 'quintic']
    for interp in interp_list:
        # Note 1: The Lanczos interpolants pass these tests just fine.  They just take a long 
        # time to run, even with the small images we are working with.  So skip them for regular 
        # unit testing.  Developers working on this should re-enable those while testing.

        # Note 2: I couldn't get 'nearest' to pass the tests.  Specifically the im3 == im4 test.
        # I don't know whether there is a bug in the Nearest class functions (seems unlikely since
        # they are so simple) or in the real-space convolver or if the nature of the Nearest
        # interpolation (with its very large extent in k-space and hard edges in real space) is 
        # such that we don't actually expect the test to pass.  Anyway, it also takes a very long 
        # time to run (before failing), so it's probably not a good idea to use it for 
        # real-space convolution anyway.

        print 'interp = ',interp

        gal = galsim.InterpolatedImage(gal_im, x_interpolant=interp)

        # First convolve with a Gaussian:
        psf = psf1
        c1 = galsim.Convolve([gal,psf], real_space=True)
        c2 = galsim.Convolve([gal,psf], real_space=False)

        im1 = c1.drawImage(scale=target_scale, nx=target_size, ny=target_size, method='no_pixel')
        im2 = c2.drawImage(scale=target_scale, nx=target_size, ny=target_size, method='no_pixel')
        np.testing.assert_array_almost_equal(im1.array, im2.array, 5)

        # Now make the psf also an InterpolatedImage:
        psf=galsim.InterpolatedImage(psf_im, x_interpolant=interp, flux=1)
        c3 = galsim.Convolve([gal,psf], real_space=True)
        c4 = galsim.Convolve([gal,psf], real_space=False)

        im3 = c3.drawImage(scale=target_scale, nx=target_size, ny=target_size, method='no_pixel')
        im4 = c4.drawImage(scale=target_scale, nx=target_size, ny=target_size, wmult=5,
                           method='no_pixel')
        np.testing.assert_array_almost_equal(im1.array, im3.array, 2)
        # Note: only 2 d.p. since the interpolated image version of the psf is really a different
        # profile from the original.  Especially for the lower order interpolants.  So we don't
        # expect these images to be equal to many decimal places.
        np.testing.assert_array_almost_equal(im3.array, im4.array, 5)

        do_pickle(c1, lambda x: x.xValue(1.123,-0.179))
        do_pickle(c3, lambda x: x.xValue(0.439,4.234))
        do_pickle(c1)
        do_pickle(c3)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_Cubic_ref():
    """Test use of Cubic interpolant against some reference values
    """
    import time
    t1 = time.time()

    interp = galsim.Cubic(tol=1.e-4)
    testobj = galsim.InterpolatedImage(ref_image, x_interpolant=interp, scale=scale,
                                       normalization='sb')
    testKvals = np.zeros(len(KXVALS))
    # Make test kValues
    for i in xrange(len(KXVALS)):
        posk = galsim.PositionD(KXVALS[i], KYVALS[i])
        testKvals[i] = np.abs(testobj.kValue(posk))
    # Compare with saved array
    refKvals = np.loadtxt(os.path.join(TESTDIR, "absfKCubic_test.txt"))
    print 'ref = ',refKvals
    print 'test = ',testKvals
    print 'kValue(0) = ',testobj.kValue(galsim.PositionD(0.,0.))
    np.testing.assert_array_almost_equal(
            refKvals/testKvals, 1., 5,
            err_msg="kValues do not match reference values for Cubic interpolant.")

    do_pickle(testobj, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(testobj)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_Quintic_ref():
    """Test use of Quintic interpolant against some reference values
    """
    import time
    t1 = time.time()

    interp = galsim.Quintic(tol=1.e-4)
    testobj = galsim.InterpolatedImage(ref_image, x_interpolant=interp, scale=scale,
                                       normalization='sb')
    testKvals = np.zeros(len(KXVALS))
    # Make test kValues
    for i in xrange(len(KXVALS)):
        posk = galsim.PositionD(KXVALS[i], KYVALS[i])
        testKvals[i] = np.abs(testobj.kValue(posk))
    # Compare with saved array
    refKvals = np.loadtxt(os.path.join(TESTDIR, "absfKQuintic_test.txt"))
    print 'ref = ',refKvals
    print 'test = ',testKvals
    np.testing.assert_array_almost_equal(
            refKvals/testKvals, 1., 5,
            err_msg="kValues do not match reference values for Quintic interpolant.")

    do_pickle(testobj, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(testobj)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_Lanczos5_ref():
    """Test use of Lanczos5 interpolant against some reference values
    """
    import time
    t1 = time.time()

    interp = galsim.Lanczos(5, conserve_dc=False, tol=1.e-4)
    testobj = galsim.InterpolatedImage(ref_image, x_interpolant=interp, scale=scale,
                                       normalization='sb')
    testKvals = np.zeros(len(KXVALS))
    # Make test kValues
    for i in xrange(len(KXVALS)):
        posk = galsim.PositionD(KXVALS[i], KYVALS[i])
        testKvals[i] = np.abs(testobj.kValue(posk))
    # Compare with saved array
    refKvals = np.loadtxt(os.path.join(TESTDIR, "absfKLanczos5_test.txt"))
    print 'ref = ',refKvals
    print 'test = ',testKvals
    np.testing.assert_array_almost_equal(
            refKvals/testKvals, 1., 5,
            err_msg="kValues do not match reference values for Lanczos-5 interpolant.")

    do_pickle(testobj, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(testobj)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)
    

def test_Lanczos7_ref():
    """Test use of Lanczos7 interpolant against some reference values
    """
    import time
    t1 = time.time()

    interp = galsim.Lanczos(7, conserve_dc=False, tol=1.e-4)
    testobj = galsim.InterpolatedImage(ref_image, x_interpolant=interp, scale=scale,
                                       normalization='sb')
    testKvals = np.zeros(len(KXVALS))
    # Make test kValues
    for i in xrange(len(KXVALS)):
        posk = galsim.PositionD(KXVALS[i], KYVALS[i])
        testKvals[i] = np.abs(testobj.kValue(posk))
    # Compare with saved array
    refKvals = np.loadtxt(os.path.join(TESTDIR, "absfKLanczos7_test.txt"))
    print 'ref = ',refKvals
    print 'test = ',testKvals
    np.testing.assert_array_almost_equal(
            refKvals/testKvals, 1., 5,
            err_msg="kValues do not match reference values for Lanczos-7 interpolant.")

    do_pickle(testobj, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(testobj)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)


def test_conserve_dc():
    """Test that the conserve_dc option for Lanczos does so.
    Note: the idea of conserving flux is a bit of a misnomer.  No interpolant does so
    precisely in general.  What we are really testing is that a flat background input
    image has a relatively flat output image.
    """
    import time
    t1 = time.time()
    import numpy

    im1_size = 40
    scale1 = 0.23
    init_val = 1.

    im2_size = 100
    scale2 = 0.011  

    im1 = galsim.ImageF(im1_size, im1_size, scale=scale1, init_value=init_val)

    # im2 has a much smaller scale, but the same size, so interpolating an "infinite" 
    # constant field.
    im2 = galsim.ImageF(im2_size, im2_size, scale=scale2)

    for interp in ['linear', 'cubic', 'quintic']:
        print 'Testing interpolant ',interp
        obj = galsim.InterpolatedImage(im1, x_interpolant=interp, normalization='sb')
        obj.drawImage(im2, method='sb')
        print 'The maximum error is ',numpy.max(abs(im2.array-init_val))
        numpy.testing.assert_array_almost_equal(
                im2.array,init_val,5,
                '%s did not preserve a flat input flux using xvals.'%interp)

        # Convolve with a delta function to force FFT drawing.
        delta = galsim.Gaussian(sigma=1.e-8)
        obj2 = galsim.Convolve([obj,delta])
        obj2.drawImage(im2, method='sb')
        print 'The maximum error is ',numpy.max(abs(im2.array-init_val))
        numpy.testing.assert_array_almost_equal(
                im2.array,init_val,5,
                '%s did not preserve a flat input flux using uvals.'%interp)

        do_pickle(obj, lambda x: x.drawImage(method='no_pixel'))
        do_pickle(obj2, lambda x: x.drawImage(method='no_pixel'))
        do_pickle(obj)
        do_pickle(obj2)


    for n in [3,4,5,6,7,8]:  # n=8 tests the generic formulae, since not specialized.
        print 'Testing Lanczos interpolant with n = ',n
        lan = galsim.Lanczos(n, conserve_dc=True)
        obj = galsim.InterpolatedImage(im1, x_interpolant=lan, normalization='sb')
        obj.drawImage(im2, method='sb')
        print 'The maximum error is ',numpy.max(abs(im2.array-init_val))
        numpy.testing.assert_array_almost_equal(
                im2.array,init_val,5,
                'Lanczos %d did not preserve a flat input flux using xvals.'%n)
    
        # Convolve with a delta function to force FFT drawing.
        delta = galsim.Gaussian(sigma=1.e-8)
        obj2 = galsim.Convolve([obj,delta])
        obj2.drawImage(im2, method='sb')
        print 'The maximum error is ',numpy.max(abs(im2.array-init_val))
        numpy.testing.assert_array_almost_equal(
                im2.array,init_val,5,
                'Lanczos %d did not preserve a flat input flux using uvals.'%n)

        do_pickle(obj, lambda x: x.drawImage(method='no_pixel'))
        do_pickle(obj2, lambda x: x.drawImage(method='no_pixel'))
        do_pickle(obj)
        do_pickle(obj2)
 
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_stepk_maxk():
    """Test options to specify (or not) stepk and maxk.
    """
    import time
    t1 = time.time()
    import numpy

    scale = 0.18
    n = 101 # use an odd number so profile doesn't get recentered at all, modifying stepk

    obj = galsim.Exponential(half_light_radius=2.*scale)
    im = galsim.Image(n, n)
    im = obj.drawImage(image=im, scale=scale)
    int_im = galsim.InterpolatedImage(im)

    step_k_val = int_im.stepK()
    max_k_val = int_im.maxK()

    mult_val = 0.9
    new_int_im = galsim.InterpolatedImage(im, _force_stepk=mult_val*step_k_val,
                                          _force_maxk=mult_val*max_k_val)
    numpy.testing.assert_almost_equal(
        new_int_im.stepK(), mult_val*step_k_val, decimal=7,
        err_msg='InterpolatedImage did not adopt forced value for stepK')
    numpy.testing.assert_almost_equal(
        new_int_im.maxK(), mult_val*max_k_val, decimal=7,
        err_msg='InterpolatedImage did not adopt forced value for maxK')

    do_pickle(int_im, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(new_int_im, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(int_im)
    do_pickle(new_int_im)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_kround_trip():
    a = final
    real_a, imag_a = a.drawKImage()
    b = galsim.InterpolatedKImage(real_a, imag_a)

    # Check picklability
    do_pickle(b)
    do_pickle(b, lambda x: x.drawImage())
    # do_pickle(b.SBProfile)
    # do_pickle(b.SBProfile, lambda x: repr(x))

    for kx, ky in zip(KXVALS, KYVALS):
        np.testing.assert_almost_equal(a.kValue(kx, ky), b.kValue(kx, ky), 2, 
            err_msg=("InterpolatedKImage evaluated incorrectly at ({:0},{:1})"
                     .format(kx, ky)))

    np.testing.assert_almost_equal(a.getFlux(), b.getFlux(), 6) #Fails at 7th decimal
    
    real_b, imag_b = b.drawKImage(real_a.copy(), imag_a.copy())
    # Fails at 4th decimal
    np.testing.assert_array_almost_equal(real_a.array, real_b.array, 3,
                                         "InterpolatedKImage kimage drawn incorrectly.") 
    # Fails at 4th decimal
    np.testing.assert_array_almost_equal(imag_a.array, imag_b.array, 3,
                                         "InterpolatedKImage kimage drawn incorrectly.")
    
    img_a = a.drawImage()
    img_b = b.drawImage(img_a.copy())
    # This is the one that matters though; fails at 6th decimal
    np.testing.assert_array_almost_equal(img_a.array, img_b.array, 5,
                                         "InterpolatedKImage image drawn incorrectly.")

    # Try some (slightly larger maxk) non-even kimages:
    for dx, dy in zip((2,3,3), (3,2,3)):
        shape = real_a.array.shape
        real_a, imag_a = a.drawKImage(nx=shape[1]+dx, ny=shape[0]+dy, scale=real_a.scale)
        b = galsim.InterpolatedKImage(real_a, imag_a)
    
        np.testing.assert_almost_equal(a.getFlux(), b.getFlux(), 6) #Fails at 7th decimal
        img_b = b.drawImage(img_a.copy())
        # One of these fails in 0.02% of pixels at 6th decimal
        np.testing.assert_array_almost_equal(img_a.array, img_b.array, 5)

    # Try some additional transformations:
    a = a.shear(g1=0.2, g2=-0.2).shift(1.1, -0.2).dilate(0.7)
    b = b.shear(g1=0.2, g2=-0.2).shift(1.1, -0.2).dilate(0.7)
    img_a = a.drawImage()
    img_b = b.drawImage(img_a.copy())
    # Fails at 6th decimal
    np.testing.assert_array_almost_equal(img_a.array, img_b.array, 5,
                                         "Transformed InterpolatedKImage image drawn incorrectly.")

    
if __name__ == "__main__":
    test_roundtrip()
    test_fluxnorm()
    test_exceptions()
    test_operations_simple()
    test_operations()
    test_uncorr_padding()
    test_pad_image()
    test_corr_padding()
    test_realspace_conv()
    test_Cubic_ref()
    test_Quintic_ref()
    test_Lanczos5_ref()
    test_Lanczos7_ref()
    test_conserve_dc()
    test_stepk_maxk()
    test_kround_trip()
