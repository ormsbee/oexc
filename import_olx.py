"""
TODO: We should allow them to specify a tar.gz, zip, or course_dir

Entry points:

1. Top level directory read
2. XML attributes
3. Finalize

"""
from datetime import datetime
import pathlib

import apsw
import click

from oexc.schema import init_db, read_static_files, read_course_metadata, read_html, read_problem, read_video, parallel_read_static_files, mm_read_static_files, lazy_read_static_files

@click.command()
@click.argument(
    'import_course_dir',
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True)
)
@click.argument(
    'output_file_path',
    type=click.Path(allow_dash=False, dir_okay=False, file_okay=True, writable=True)
)
def import_olx(import_course_dir, output_file_path):
    # We're going to overwrite anything that was there, so delete if it exists.
    pathlib.Path(output_file_path).unlink(missing_ok=True)
    course_dir = pathlib.Path(import_course_dir)

    conn = apsw.Connection(output_file_path)
    init_db(conn)
    print(datetime.now())

    course_key = read_course_metadata(course_dir, conn)
    print(datetime.now())

    read_static_files(course_dir, conn)
    # mm_read_static_files(course_dir, conn)
    # parallel_read_static_files(course_dir, conn)
    # lazy_read_static_files(course_dir, conn)
    print(datetime.now())

    read_html(course_dir, conn, course_key)
    print(datetime.now())

    read_problem(course_dir, conn, course_key)
    print(datetime.now())

    read_video(course_dir, conn, course_key)
    print(datetime.now())

    # Step 1: Get basic high-level Course metadata, like what run we have.

    # Step 2: Bring in all the static files. Putting these in first allows us
    # to link them to various blocks if we process them afterwards.

    # Step 3: Get the leaf nodes: HTML,

    print("Hello World!")
    print(type(import_course_dir))
    print(import_course_dir)


if __name__ == "__main__":
    import_olx()
