"""Management of the metadata database"""

import json
import collections
import builtins
import os
import functools
import operator
import io
import gzip

import util.misc
from . import md_utils

import fs
import fs_s3fs

def metadata_dir():
    """Returns the directory to which metadata was recorded, as specified by the environment variable VIRAL_NGS_METADATA_PATH.
    Raises an error if the environment variable is not defined.
    """
    return os.environ['VIRAL_NGS_METADATA_PATH']

def metadata_dir_sanitized():
    """Return version `metadata_dir()` suitable for display in log messsages.  Any sensitive information like AWS keys will be scrubbed."""
    return md_utils._mask_secret_info(metadata_dir())

def is_metadata_tracking_enabled():
    return 'VIRAL_NGS_METADATA_PATH' in os.environ

def is_valid_step_record(d):
    """Test whether `d` is a dictionary containing all the expected elements of a step, as recorded by the code above"""
    return md_utils.dict_has_keys(d, 'format step') and \
        md_utils.dict_has_keys(d['step'], 'args step_id cmd_module')

def load_all_records():
    """Load all step records from the database.  If multiple databases are active, only load from the last one."""

    records = []
    with fs.open_fs(metadata_dir().split()[-1]) as metadata_fs:
        for f in sorted(metadata_fs.listdir(u'/')):
            if f.endswith('.json.gz'):
                json_data_gzipped = metadata_fs.getbytes(f)
                with io.BytesIO(json_data_gzipped) as fgz:
                    with gzip.GzipFile(mode='rb', fileobj=fgz) as gzip_obj:
                        json_bytes = gzip_obj.read()
                json_str = json_bytes.decode()
                step_record = md_utils.byteify(json.loads(json_str))
                if is_valid_step_record(step_record):
                    records.append(step_record)
    return records

def load_step_record(step_id):
    """Load one step record from the database"""
    json_fname = u'{}.json.gz'.format(step_id)
    with fs.open_fs(metadata_dir().split()[-1]) as metadata_fs:
        json_str = metadata_fs.gettext(json_fname)
        step_record = md_utils.byteify(json.loads(json_str))
        assert is_valid_step_record(step_record)
        return step_record

def store_step_record(step_data, write_obj):
    """Store step record to metadata database(s)"""
    json_fname = u'{}.json.gz'.format(step_data['step']['step_id'])
    json_str = json.dumps(step_data, sort_keys=True, indent=4, default=write_obj)
    json_bytes = unicode(json_str) if hasattr(builtins, 'unicode') else json_str.encode('utf-8')

    fgz = io.BytesIO()
    with gzip.GzipFile(filename=json_fname, mode='wb', fileobj=fgz) as gzip_obj:
        gzip_obj.write(json_bytes)
    json_data_gzipped = fgz.getvalue()

    for mdir in metadata_dir().split():
        with fs.open_fs(mdir) as metadata_fs:
            metadata_fs.setbytes(json_fname, json_data_gzipped)


