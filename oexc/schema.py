"""
Apps (in run/dependency order)

- openedx.contexts
- openedx.courses

- openedx.assets
- openedx.items
- openedx.units

- openedx.sequences

- openedx.content_groups
- openedx.scheduling
- openedx.grades
- openedx.search


- extras (e.g. mathjax)

Questions:
* Namespacing?
* Multiple contexts?

* Is the relationship between parent/child intrinsic to the content itself or
  context specific? The former is more intuitive, but the latter would allow us
  to create multiple aliases of the same base content with different policy and
  place them in different hierarchies.
  -- Do the usage key. More flexible, not much more complex.

  policy is associated with the usage key directly -- inheritance is not a thing
  - optimize for lms runtime access pattern
  - make unambiguous

* Content item is almost a conten ATOM, but unreferencable on its own.

* null order number means it's not an ordered collection, like a set of possible children.
* make a table with all child lookups, so no need for fancy CTEs?
* - no, you need the explicit parent->child relation anyway

This means sequences have any arbitrary context_content_item as a child. Units
aren't special, particulary.

* Multilingual?



"""
import xml.etree.ElementTree as ET
import pathlib

import apsw
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator


def init_db(conn):
    """
    Create the bare tables we need to bootstrap the process.

    This includes the table for keeping track of the active versions of apps
    that we're going to load into the file.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
--        PRAGMA journal_mode = TRUNCATE;
--        PRAGMA locking_mode=EXCLUSIVE;
        PRAGMA page_size=65536;
        PRAGMA synchronous=0;

        BEGIN TRANSACTION;

        -- Top level bookkeeping
        create table openedx_core_app(
            id integer primary key,
            name text not null,
            version integer not null,
            url text
        );
        create unique index idx_openedx_core_app_name on openedx_core_app(name);

        -- Should put a hash of the content here
        create table openedx_core_context(
            id integer primary key,
            ext_id text not null,
            type text not null,
            version text not null,
            title text
        );
        create unique index idx_openedx_core_context_ext_id
            on openedx_core_context(ext_id);

        insert into openedx_core_app
            (name, version, url)
        values
            ('openedx.core', 1, 'https://docs.edx.org/???');

        -- Course
        create table openedx_courses_config(
            course_id integer not null,
            key text not null,
            value json,
            foreign key (course_id) references openedx_core_context(id)
        );
        create unique index idx_openedx_courses_config_course_id_key
            on openedx_courses_config(course_id, key);

        insert into openedx_core_app
            (name, version, url)
        values
            ('openedx.courses', 1, 'https://docs.edx.org/???');

        -- Static assets
        create table openedx_assets_file(
            id integer primary key,
--            ext_id text not null,
            file_path text not null,
            size integer not null,
            mime_type text,
            title text,
            description text,
            content blob not null
        );

        insert into openedx_core_app
            (name, version, url)
        values
            ('openedx.assets', 1, 'https://docs.edx.org/???');

        -- Content Item
        create table openedx_content_item(
            id integer primary key,
            natural_key text,
            type text not null,
            title text,
            definition text
        );

        create table openedx_content_item_children(
            parent_id integer,
            child_id integer,
            order_num integer
        );
        create unique index idx_openedx_content_item_children_parent_to_children
            on openedx_content_item_children(parent_id, child_id, order_num);
        create index idx_openedx_content_item_children_child_to_parent
            on openedx_content_item_children(child_id, parent_id);

        -- The natural key for the definition should ideally be something like
        -- a UUID, since the addressable thing will be the context-aware reference from context_item
        create table openedx_content_context_item(
            context_id integer not null,
            item_id integer not null,
            natural_key text not null,
            slug text,

            foreign key (context_id) references openedx_core_context(id),
            foreign key (item_id) references openedx_content_item(id)
        );
        create unique index idx_openedx_content_context_item_context_and_item
            on openedx_content_context_item(context_id, item_id);
        create unique index idx_openedx_content_context_item_context_and_natural_key
            on openedx_content_context_item(context_id, natural_key);
        create unique index idx_openedx_content_context_item_context_and_slug
            on openedx_content_context_item(context_id, slug);

        create index idx_openedx_content_context_item_item_id
            on openedx_content_context_item(item_id);
        create index idx_openedx_content_context_item_natural_key
            on openedx_content_context_item(natural_key);

        COMMIT;
        """
    )


def lazy_read_static_files(course_dir, conn):
    static_dir = course_dir / "static"

    cursor = conn.cursor()
    cursor.execute("BEGIN")
    asset_file_paths = [
        file_path
        for file_path in sorted(static_dir.rglob('*'))
        if file_path.is_file() and file_path.name != '.DS_Store'
    ]

    for file_path in asset_file_paths:
        cursor.execute(
            """
            insert into openedx_assets_file
                (file_path, size, content)
            values
                (?, ?, ?)
            """,
            (
                str(file_path.relative_to(static_dir)),
                file_path.stat().st_size,
                file_path.read_bytes(),
            )
        )
    cursor.execute("COMMIT")


def read_static_files(course_dir, conn):
    static_dir = course_dir / "static"

    cursor = conn.cursor()
    cursor.execute("BEGIN")
    asset_file_paths = [
        file_path
        for file_path in sorted(static_dir.rglob('*'))
        if file_path.is_file() and file_path.name != '.DS_Store'
    ]

    for file_path in asset_file_paths:
        with open(file_path, 'rb') as asset_file:
            asset_data = asset_file.read()
            cursor.execute(
                """
                insert into openedx_assets_file
                    (file_path, size, content)
                values
                    (?, ?, ?)
                """,
                (
                    str(file_path.relative_to(static_dir)),
                    len(asset_data),
                    asset_data,
                )
            )
    cursor.execute("COMMIT")


import mmap

def mm_read_static_files(course_dir, conn):
    static_dir = course_dir / "static"

    cursor = conn.cursor()
    cursor.execute("BEGIN")
    asset_file_paths = [
        file_path
        for file_path in sorted(static_dir.rglob('*'))
        if file_path.is_file() and file_path.name != '.DS_Store'
    ]

    for file_path in asset_file_paths:
        with open(file_path, 'r+b') as asset_file:
            mm = mmap.mmap(asset_file.fileno(), 0, prot=mmap.PROT_READ)
            cursor.execute(
                """
                insert into openedx_assets_file
                    (file_path, size, content)
                values
                    (?, ?, ?)
                """,
                (
                    str(file_path.relative_to(static_dir)),
                    0,
                    bytes(mm),
                )
            )
            mm.close()
            print(file_path)
    cursor.execute("COMMIT")



from multiprocessing import Pool


def read_file_data(file_path):
    with open(file_path, 'rb') as asset_file:
        asset_data = asset_file.read()
    return (file_path, asset_data)

def parallel_read_static_files(course_dir, conn):
    static_dir = course_dir / "static"

    cursor = conn.cursor()
    cursor.execute("BEGIN")
    asset_file_paths = [
        file_path
        for file_path in sorted(static_dir.rglob('*'))
        if file_path.is_file() and file_path.name != '.DS_Store'
    ]

    pool = Pool(4)
    for file_path, asset_data in pool.imap_unordered(read_file_data, asset_file_paths):
        cursor.execute(
            """
            insert into openedx_assets_file
                (file_path, size, content)
            values
                (?, ?, ?)
            """,
            (
                str(file_path.relative_to(static_dir)),
                len(asset_data),
                buffer(asset_data),
            )
        )

    cursor.execute("COMMIT")


def read_html(course_dir, conn, course_key):
    html_dir = course_dir / "html"
    xml_file_paths = [file_path for file_path in sorted(html_dir.glob("*.xml"))]

    cursor = conn.cursor()
    cursor.execute("BEGIN")

    for file_path in xml_file_paths:
        # print(file_path)
        # Should we leave missing things as empty strings or null?
        title = ET.parse(file_path).getroot().attrib.get('display_name')
        html_file_path = file_path.with_suffix('.html')
        with open(html_file_path, 'rb') as html_file:
            html_content = html_file.read()
        cursor.execute(
            """
            insert into openedx_content_item
                (natural_key, type, title, definition)
            values
                (?, ?, ?, ?);
            """,
            (
#                f"html+block@{file_path.stem}",
                file_path.stem,
                "xblock/html",
                title,
                html_content
            )
        )
        insert_course_item(
            cursor,
            conn.last_insert_rowid(),
            BlockUsageLocator(course_key, 'html', file_path.stem),
        )

#conn.last_insert_rowid()

    cursor.execute("COMMIT")


def read_problem(course_dir, conn, course_key):
    """

    Problems have policies unlike most things -– the retry stuff only really applies here...
    """
    problem_dir = course_dir / "problem"
    xml_file_paths = [file_path for file_path in sorted(problem_dir.glob("*.xml"))]

    cursor = conn.cursor()
    cursor.execute("BEGIN")

    for file_path in xml_file_paths:
        # print(file_path)
        title = ET.parse(file_path).getroot().attrib.get('display_name')
        with open(file_path, 'rb') as olx_file:
            olx_content = olx_file.read()
        cursor.execute(
            """
            insert into openedx_content_item
                (natural_key, type, title, definition)
            values
                (?, ?, ?, ?);
            """,
            (
#                f"problem+block@{file_path.stem}",
                file_path.stem,
                "xblock/problem",
                title,
                olx_content
            )
        )
        insert_course_item(
            cursor,
            conn.last_insert_rowid(),
            BlockUsageLocator(course_key, 'problem', file_path.stem),
        )

    cursor.execute("COMMIT")


def read_video(course_dir, conn, course_key):
    """

    Problems have policies unlike most things -– the retry stuff only really applies here...
    """
    blocks_dir = course_dir / "video"
    xml_file_paths = [file_path for file_path in sorted(blocks_dir.glob("*.xml"))]

    cursor = conn.cursor()
    cursor.execute("BEGIN")

    for file_path in xml_file_paths:
        # print(file_path)
        title = ET.parse(file_path).getroot().attrib.get('display_name')
        with open(file_path, 'rb') as olx_file:
            olx_content = olx_file.read()
        cursor.execute(
            """
            insert into openedx_content_item
                (natural_key, type, title, definition)
            values
                (?, ?, ?, ?);
            """,
            (
#                f"video+block@{file_path.stem}",
                file_path.stem,
                "xblock/video",
                title,
                olx_content
            )
        )
        insert_course_item(
            cursor,
            conn.last_insert_rowid(),
            BlockUsageLocator(course_key, 'video', file_path.stem),
        )

    cursor.execute("COMMIT")


def read_unit(course_dir, conn, course_key):
    units_dir = course_dir / "video"
    xml_file_paths = [file_path for file_path in sorted(units_dir.glob("*.xml"))]

    cursor = conn.cursor()
    cursor.execute("BEGIN")

    for file_path in xml_file_paths:
        # print(file_path)
        vertical_el = ET.parse(file_path).getroot().attrib.get('display_name')
        title = vertical_el.attrib.get('display_name')
        for child_el in vertical_el:
            if child_el.attrib.keys() == {'url_name'}:
                pass

        with open(file_path, 'rb') as olx_file:
            olx_content = olx_file.read()
        cursor.execute(
            """
            insert into openedx_content_item
                (natural_key, type, title, definition)
            values
                (?, ?, ?, ?);
            """,
            (
#                f"video+block@{file_path.stem}",
                file_path.stem,
                "xblock/video",
                title,
                olx_content
            )
        )
        insert_course_item(
            cursor,
            conn.last_insert_rowid(),
            BlockUsageLocator(course_key, 'video', file_path.stem),
        )

    cursor.execute("COMMIT")



def insert_course_item(cursor, item_id, usage_key):
    cursor.execute(
        """
        insert into openedx_content_context_item
            (context_id, item_id, natural_key)
        values
            (?, ?, ?)
        """,
        (
            1,
            item_id,
            str(usage_key),
        )
    )


def read_course_metadata(course_dir, conn):
    course_file_path = course_dir / "course.xml"
    course_el = ET.parse(course_file_path).getroot()
    course_key = CourseLocator(
        org=course_el.attrib['org'],
        course=course_el.attrib['course'],
        run=course_el.attrib['url_name'],
    )

    full_course_el = ET.parse(course_dir / "course" / f"{course_key.run}.xml").getroot()
    course_attribs = full_course_el.attrib
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    cursor.execute(
        "insert into openedx_core_context (ext_id, type, version, title) values (?, ?, ?, ?)",
        (
            str(course_key),
            "course",
            "(published_version_hash_here)",
            course_attribs.pop('display_name'),
        )
    )

    # This is actually kind of an anti-pattern. Pretty much everything here
    # should be done as separate apps.
    for key, val in sorted(course_attribs.items()):
        cursor.execute(
            "insert into openedx_courses_config (course_id, key, value) values (1, ?, ?)",
            (
                key,
                val,
            )
        )
    cursor.execute("COMMIT")

    return course_key


class App:
    def __init__(self, db_conn):
        self.db_conn = db_conn


class ContextApp(App):
    """
        create table context(
            id integer primary key,

        )


    """
    def init_db(self):
        self.db_conn.cursor()
        cursor.execute(

        )

    def add_context():
        pass


class CourseImporter:
    pass