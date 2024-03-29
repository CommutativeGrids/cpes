from operator import itemgetter
from random import choice

import matplotlib.pyplot as plt
import numpy as np
import random
from rdfpy import rdf
from scipy.spatial.distance import euclidean
from sklearn.metrics.pairwise import euclidean_distances
import plotly.express as px
import numpy as np
from scipy.signal import argrelextrema


def distance_array(data, n=20):
    """
    returns the distance between atoms in increasing order
    By default only the smallest 20 values are returned
    """
    dist_array = euclidean_distances(data).flatten()
    result = np.array(list(set(np.around(dist_array, decimals=4))))
    result.sort()
    return result[:n]


def rdf_plot(data, start=2, end=6, step=0.05, divided_by_2=True):
    """
    plot the radial distribution function
    point cloud needs to be centered
    The result is orientation dependent
    Step shall not be too small
    """
    center = data[center_point_cloud(data)]
    print(f"center of the point cloud is {center}")
    print("The point cloud should be centered around the origin.")
    points = data
    g_r, radii = rdf(points, dr=step)
    number_pts_per_unit = int(1 / step)
    index_left = max(0, int(start * number_pts_per_unit) - 5)
    index_right = number_pts_per_unit * end + 5
    x_coords = radii[index_left:index_right]
    y_coords = g_r[index_left:index_right]
    if divided_by_2:
        x_coords /= 2
    fig = px.line(x=x_coords, y=y_coords, title='Radial Distribution Function')
    # define local peaks to be points in zip(x_coords, y_coords) with y_coords not smaller 
    # than both the previous and the next y_coords
    local_peaks_indices = argrelextrema(y_coords, np.greater)
    local_peaks=np.array(list(zip(x_coords,y_coords)))[local_peaks_indices]
    fig.add_scatter(x=local_peaks[:,0], y=local_peaks[:,1], mode='markers', marker=dict(size=5, color='red'),name='Peaks')
    
    return (fig,local_peaks)


def coordination_number(data, crictical_value, anchor="random"):
    """
    Return the number of atoms within radius crictical_value of the anchor.
    When crictical_value is the shortest distance between two atoms, this function
    returns the coordination number of the anchor atom.

    coordination number of the anchor atom in the data.
    result may change when using random mode
    """
    if anchor == "random":
        center_atom = [choice(data)]
    else:
        center_atom = [np.array(anchor).flatten()]
    # TODO remove boundary atoms (or atoms close to the boundary)
    print(center_atom)
    dist_vec = euclidean_distances(center_atom, data).flatten()
    count = 0
    for i in dist_vec:
        if i < 1.001 * crictical_value:
            count += 1
    return count - 1  # minus itself


def sphere_confine(data, radius):
    """confine the data to a sphere with the given radius
    """
    return np.array([pt for pt in data if np.linalg.norm(pt) < radius])


def plot_3d(data):
    """plot data in 3d
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(data[:, 0], data[:, 1], data[:, 2], alpha=0.8, s=300.0)
    plt.show()


def center_point_cloud(data):
    """return the index of the point closest to the center of the point cloud
    """
    mass_center = np.mean(data, axis=0)
    return np.argmin(euclidean_distances([mass_center], data))


def atomic_packing_factor(data, radius=1):
    """returns the atomic packing factor
    """
    x, y, z = zip(*data)
    a, b = [(min(x), min(y), min(z)), (max(x), max(y), max(z))]
    # a,b,c=(max(x)-min(x), max(y)-min(y), max(z)-min(z))
    total = (
        np.sqrt(3) * euclidean(a, b) ** 3 / 9.0
    )  # volume computed from the body diagonal
    # volume of the bounding box to be optimized.
    occupied = 4 * np.pi / 3 * len(data) * radius ** 3  # volume of the occupied region
    return occupied / total


def thinning_aux(df, survival_rate=None, number_removal=None, style="homcloud", is_removable=None):
    """delete points randomly from data.

    Parameters
    ----------
    data : ndarray
        the data to be thinned
    survival_rate : float
        percentage of points to survive
    style : str, optional
        the style of thinning. The default is 'homcloud'.
        'homcloud' : remained points will be labelled 0.
        'survived' : only returns the survived points.
    is_removable: str, or list of str, optional
        name of the column to be used as the removal criteria.
    The meaning of 間引き率 in the paper may lead different understandings
    (for example see table 1 in section 4 of the paper below:
    https://www.jstage.jst.go.jp/article/jsiamt/3/2/3_KJ00002977660/_pdf/-char/ja)
    """
    assert number_removal is None or number_removal >=0
    assert survival_rate is None or 0 <= survival_rate <= 1
    # generate the index list for random removal
    if is_removable is None:
        removable_index_list=list(df.index)
        nonremovable_index_list=[]
    else:
        if isinstance(is_removable, str):
            if is_removable not in df.columns:
                raise ValueError(f"{is_removable} is not in the dataframe")
            removable_index_list = list(df.loc[df[is_removable]==True].index)
            nonremovable_index_list = list(df.loc[df[is_removable]==False].index)
        if isinstance(is_removable, list):
            removable_index_list = list(df.loc[df[is_removable].all(axis=1)].index)
            nonremovable_index_list = list(df.loc[df[is_removable].all(axis=1)].index)

    if number_removal is None:
        # number of points to be removed is calculated based on the total number of points
        number_removal = int(len(df.index) * (1 - survival_rate)) 
    number_remained = int(len(removable_index_list) - number_removal)
    removable_index_remained = random.sample(removable_index_list, number_remained) # sampling without duplicates
    index_remained = [*removable_index_remained,*nonremovable_index_list]

    #np.random.choice(df_length, number_remained, replace=False)
    if style == "homcloud":
        def label_rule(i):
            if i in index_remained:
                return 0
            else:
                return 1
        labelled_data = [(label_rule(i), *vec) for i, vec in enumerate(df[['x', 'y', 'z']].values)]
        sorted_result = np.array(sorted(labelled_data, key=itemgetter(0)))
        return (df.loc[index_remained], sorted_result)
    elif style == "survived":
        return (df.loc[index_remained], None)
    else:
        raise NotImplementedError
