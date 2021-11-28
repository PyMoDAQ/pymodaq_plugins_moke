import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
from PIL import Image, ImageDraw, ImageFilter


def koch_line(start, end, factor):
    """
    Segments a line to Koch line, creating fractals.


    :param tuple start:  (x, y) coordinates of the starting point
    :param tuple end: (x, y) coordinates of the end point
    :param float factor: the multiple of sixty degrees to rotate
    :returns tuple: tuple of all points of segmentation
    """

    # coordinates of the start
    x1, y1 = start[0], start[1]

    # coordinates of the end
    x2, y2 = end[0], end[1]

    # the length of the line
    l = np.sqrt((x2 - x1 )**2 + (y2 - y1 )**2)

    # first point: same as the start
    a = (x1, y1)

    # second point: one third in each direction from the first point
    b = (x1 + (x2 - x1 ) /3., y1 + (y2 - y1 ) /3.)

    # third point: rotation for multiple of 60 degrees
    c = (b[0] + l/ 3. * np.cos(factor * np.pi / 3.), b[1] + l / 3. * np.sin(factor * np.pi / 3.))

    # fourth point: two thirds in each direction from the first point
    d = (x1 + 2. * (x2 - x1) / 3., y1 + 2. * (y2 - y1) / 3.)

    # the last point
    e = end

    return {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'factor': factor}


def koch_snowflake(degree, s=5.0):
    """Generates all lines for a Koch Snowflake with a given degree.

    :param int degree: how deep to go in the branching process
    :param float s: the length of the initial equilateral triangle
    :returns list: list of all lines that form the snowflake
    """
    # all lines of the snowflake
    lines = []

    # we rotate in multiples of 60 degrees
    sixty_degrees = np.pi / 3.

    # vertices of the initial equilateral triangle
    A = (0., 0.)
    B = (s, 0.)
    C = (s * np.cos(sixty_degrees), s * np.sin(sixty_degrees))

    # set the initial lines
    if degree == 0:
        lines.append(koch_line(A, B, 0))
        lines.append(koch_line(B, C, 2))
        lines.append(koch_line(C, A, 4))
    else:
        lines.append(koch_line(A, B, 5))
        lines.append(koch_line(B, C, 1))
        lines.append(koch_line(C, A, 3))

    for i in range(1, degree):
        # every lines produce 4 more lines
        for _ in range( 3 * 4**(i - 1)):
            line = lines.pop(0)
            factor = line['factor']

            lines.append(koch_line(line['a'], line['b'], factor % 6))  # a to b
            lines.append(koch_line(line['b'], line['c'], (factor - 1) % 6))  # b to c
            lines.append(koch_line(line['c'], line['d'], (factor + 1) % 6))  # d to c
            lines.append(koch_line(line['d'], line['e'], factor % 6))  # d to e

    return lines


def image_from_koch(degree, flake_size=5, image_size=(256, 256), blur_radius=3):
    base = Image.new("L", image_size)
    lines = koch_snowflake(degree, flake_size)
    x, y = [], []
    for l in lines:
        x.extend([l['a'][0], l['b'][0], l['c'][0], l['d'][0], l['e'][0]])
        y.extend([l['a'][1], l['b'][1], l['c'][1], l['d'][1], l['e'][1]])
    x = np.array(x) + image_size[1] / 2 - flake_size / 2
    y = np.array(y) + image_size[0] / 2 - flake_size / np.sqrt(3) / 2
    draw = ImageDraw.Draw(base)
    draw.polygon(list(zip(x, y)), fill=256)
    return np.asarray(base.filter(ImageFilter.BoxBlur(blur_radius))) / 256


def plot_koch():
    import matplotlib.pyplot as plt

    max_degree = 10
    fig, axs = plt.subplots(1, max_degree, figsize=(5*max_degree, 5), subplot_kw={'aspect': 'equal'})
    colors = ['#661D98', '#2CBDFE', '#47DBCD', '#F5B14C', '#960019', '#661D98', '#2CBDFE', '#47DBCD', '#F5B14C', '#960019']


    for d in range(max_degree):
        lines = koch_snowflake(degree=d)

        # extract the line coordinates
        x, y = [], []
        for l in lines:
            x.extend([l['a'][0], l['b'][0], l['c'][0], l['d'][0], l['e'][0]])
            y.extend([l['a'][1], l['b'][1], l['c'][1], l['d'][1], l['e'][1]])

        # remove all ticks and axes
        axs[d].set_xticks([], [])
        axs[d].set_yticks([], [])
        axs[d].spines['right'].set_visible(False)
        axs[d].spines['left'].set_visible(False)
        axs[d].spines['top'].set_visible(False)
        axs[d].spines['bottom'].set_visible(False)

        # fill the polygons
        axs[d].fill(x, y, facecolor=colors[d], edgecolor='black', lw=1)

    plt.show()

    plt.gcf().text(0.1, 0.15, 'by Vladimir Ilievski', fontsize=28, fontfamily='Verdana')
    plt.savefig('snowflakes_0_to_4.png', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    data = image_from_koch(4, 100)
    import matplotlib.pyplot as plt
    max_degree = 10
    fig, axs = plt.subplots(1, 1, subplot_kw={'aspect': 'equal'})
    plt.imshow(data)

    fig.show()
    pass
