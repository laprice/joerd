from joerd.util import BoundingBox
from multiprocessing import Pool
from contextlib import closing
from shutil import copyfile
import os.path
import os
import requests
import logging
import re
import tempfile
import sys
import traceback
import subprocess
import glob
from osgeo import gdal


#GMTED_BASE_URL = 'http://topotools.cr.usgs.gov/GMTED_viewer/data/' \
#                 'Global_tiles_GMTED'
GMTED_BASE_URL = 'http://edcintl.cr.usgs.gov/downloads/sciweb1/shared' \
                 '/topo/downloads/GMTED/Global_tiles_GMTED'
GMTED_YS = [-90, -70, -50, -30, -10, 10, 30, 50, 70]
GMTED_XS = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]


def __download_gmted_file(x, y, base_dir):
    dir = "%s%03d" % ("E" if x >= 0 else "W", abs(x))
    res = '300' if y == -90 else '075'
    xname = "%03d%s" % (abs(x), "E" if x >= 0 else "W")
    yname = "%02d%s" % (abs(y), "N" if y >= 0 else "S")

    dname = "/%(res)sdarcsec/mea/%(dir)s/" % dict(res=res, dir=dir)
    fname = "%(y)s%(x)s_20101117_gmted_mea%(res)s.tif" % \
            dict(res=res, x=xname, y=yname)

    url = GMTED_BASE_URL + dname + fname
    output_file = os.path.join(base_dir, fname)

    if os.path.isfile(output_file):
        return output_file

    with closing(tempfile.NamedTemporaryFile()) as tmp:
        with closing(requests.get(url, stream=True)) as req:
            for chunk in req.iter_content(chunk_size=10240):
                if chunk:
                    tmp.write(chunk)
        tmp.flush()

        copyfile(tmp.name, output_file)

    return output_file


def _download_gmted_file(source_name, target_name, base_dir):
    try:
        return __download_gmted_file(source_name, target_name, base_dir)
    except:
        print>>sys.stderr, "Caught exception: %s" % ("\n".join(traceback.format_exception(*sys.exc_info())))
        raise


def _parallel(func, iterable, num_threads=None):
    p = Pool(processes=num_threads)
    threads = []

    for x in iterable:
        p.apply_async(func, x)

    p.close()
    return_values = []
    for t in threads:
        return_values.append(t.get())

    p.join()
    return return_values


class GMTED:

    def __init__(self, regions, base_dir='gmted', num_download_threads=None):
        self.regions = regions
        self.num_download_threads = num_download_threads
        self.base_dir = base_dir

    def download(self):
        logger = logging.getLogger('gmted')
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        tiles = []
        for y in GMTED_YS:
            for x in GMTED_XS:
                bbox = BoundingBox(x, y, x + 30, y + 20)
                if self._intersects(bbox):
                    tiles.append((x, y))

        logger.info("Starting download of %d GMTED files "
                         "(these are _huge_, so please be patient)."
                         % len(tiles))
        files = _parallel(_download_gmted_file,
                          [(x, y, self.base_dir) for x, y in tiles],
                          num_threads=self.num_download_threads)

        # sanity check
        for f in files:
            assert os.path.isfile(f)

        logger.info("Download complete.")

    def buildvrt(self):
        logger = logging.getLogger('gmted')
        logger.info("Creating VRT.")

        is_gmted_tif = re.compile(
            '^([0-9]{2})([NS])([0-9]{3})([EW])_'
            '20101117_gmted_mea([0-9]{3}).tif$')

        files = []
        for f in glob.glob(os.path.join(self.base_dir, '*.tif')):
            name = os.path.split(f)[1]
            m = is_gmted_tif.match(os.path.split(f)[1])
            if m:
                bbox = self._parse_bbox(*m.groups())
                if self._intersects(bbox):
                    files.append(f)

        args = ["gdalbuildvrt", "-q", self.vrt_file()] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        assert os.path.isfile(self.vrt_file())

        logger.info("VRT created.")

    def vrt_file(self):
        return os.path.join(self.base_dir, "gmted.vrt")

    def mask_negative(self):
        return True

    def filter_type(self):
        return gdal.GRA_Lanczos

    def _parse_bbox(self, ns_deg, is_ns, ew_deg, is_ew, res):
        bottom = int(ns_deg)
        left = int(ew_deg)

        if is_ns == 'S':
            bottom = -bottom
        if is_ew == 'W':
            left = -left

        b = BoundingBox(left, bottom, left + 30, bottom + 20)
        return b

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox):
                return True
        return False


def create(regions):
    return GMTED(regions)
