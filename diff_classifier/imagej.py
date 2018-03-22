import numpy as np
import sys
import os.path as op
import skimage.io as sio
import subprocess
import tempfile
import diff_classifier as dc
from sklearn.neighbors import KNeighborsClassifier
from sklearn import linear_model
from sklearn import svm


def partition_im(tiffname, irows=4, icols=4, ires=512):
    """
    partition_im(tiffname, irows=int, icols=int, ires=int)

    Partitions a 2048x2044 image into irows x icols images of size ires x ires and saved them.

    Parameters
    ----------
    tiffname : string
        Location of input image to be partitioned.
    irows : int
        Number of rows of size ires pixels to be partitioned from source image.
    icols : int
        Number of columns of size ires pixels to be partitioned from source image.
    ires : int
        Output images are of size ires x ires pixels.

    Examples
    ----------
    >>> partition_im('your/sample/image.tif', irows=8, icols=8, ires=256)

    """
    test = sio.imread(tiffname)
    test2 = np.zeros((test.shape[0], 2048, 2048), dtype=test.dtype)
    test2[:, 0:2044, :] = test

    new_image = np.zeros((test.shape[0], ires, ires), dtype=test.dtype)
    names = []

    for row in range(irows):
        for col in range(icols):
            new_image = test2[:, row*ires:(row+1)*ires, col*ires:(col+1)*ires]
            current = tiffname.split('.tif')[0] + '_%s_%s.tif' % (row, col)
            sio.imsave(current, new_image)
            names.append(current)

    return names


def mean_intensity(local_im):
    test_image = sio.imread(local_im)
    test_intensity = np.mean(test_image[0, :, :])

    return test_intensity


def track(target, out_file, template=None, fiji_bin=None, radius=2.5, threshold=5.,
          do_median_filtering=False, quality=30.0, x=511, y=511, ylo=1, median_intensity=55000.0, snr=0.0,
          linking_max_distance=10.0, gap_closing_max_distance=10.0, max_frame_gap=3,
          track_displacement=0.0):
    """

    target : str
        Full path to a tif file to do tracking on.
        Can also be a URL (e.g., 'http://fiji.sc/samples/FakeTracks.tif')
    out_file : str
        Full path to a csv file to store the results.
    template : str, optional
        The full path of a template for tracking. Defaults to use
        `data/trackmate_template.py` stored in the diff_classifier source-code.
    """
    if template is None:
        template = op.join(op.split(dc.__file__)[0],
                           'data',
                           'trackmate_template3.py')

    if fiji_bin is None:
        if sys.platform == "darwin":
            fiji_bin = op.join(
                '/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx')
        elif sys.platform.startswith("linux"):
            fiji_bin = op.join(op.expanduser('~'), 'Fiji.app/ImageJ-linux64')

    script = ''.join(open(template).readlines())
    tf = tempfile.NamedTemporaryFile(suffix=".py")
    fid = open(tf.name, 'w')
    fid.write(script.format(target_file=target, radius=str(radius), threshold=str(threshold),
                            do_median_filtering=str(do_median_filtering), quality=str(quality),
                            x = str(x), y = str(y), ylo = str(ylo),
                            median_intensity=str(median_intensity), snr=str(snr),
                            linking_max_distance=str(linking_max_distance),
                            gap_closing_max_distance=str(gap_closing_max_distance),
                            max_frame_gap=str(max_frame_gap), track_displacement=str(track_displacement)))
    fid.close()
    cmd = "%s --ij2 --headless --run %s" % (fiji_bin, tf.name)
    print(cmd)
    sp = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
    fid = open(out_file, 'w')
    fid.write(sp.stdout.decode())
    fid.close()


def regress_tracking_params(all_videos, y, training_size, have_output=True):
    """
    Uses regression techniques to select the best tracking parameters.
    Regression again intensities of input images.
    """

    tprefix = []
    for i in range(0, tnum):
        random.seed(i+1)
        tprefix.append(to_track[random.randint(0, len(to_track))])
        if have_output is False:
            print("Get parameters for: {}".format(tprefix[i]))

    if have_output is True:
        # Define descriptors
        descriptors = np.zeros((tnum, 4))
        counter = 0
        for name in tprefix:
            local_im = name + '.tif'
            test_image = sio.imread(local_im)
            descriptors[counter, 0] = np.mean(test_image[0, :, :])
            descriptors[counter, 1] = np.std(test_image[0, :, :])
            descriptors[counter, 2] = np.percentile(test_image[0, :, :], 10)
            descriptors[counter, 3] = np.percentile(test_image[0:, :, :], 90)
            counter = counter + 1

        # Define regression techniques
        X = descriptors
        classifiers = [
            svm.SVR(),
            linear_model.SGDRegressor(),
            linear_model.BayesianRidge(),
            linear_model.LassoLars(),
            linear_model.ARDRegression(),
            linear_model.PassiveAggressiveRegressor(),
            linear_model.TheilSenRegressor(),
            linear_model.LinearRegression()]