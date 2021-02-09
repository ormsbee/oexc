# Open EdX Course File Format

Maybe .oxc?

I want to create an Open edX content interchange data format with the following goals:

## Represent the structures and content supported by the platform today.

The format should support everything you can do today in an Open edX course, including more obscure things like parent/child relations in XBlocks, settings overrides on problems imported from content libraries, etc.

## Be open-ended enough to accomodate the different types of content and structures we're looking forward to.

This means both supporting organizational structures that are smaller than courses (e.g. LabXchange-style pathways), as well as having leaf content that are not XBlocks.

## Simplify the publish lifecycle.

When you publish a course today, it doesn't cleanly go from version A to version B in an atomic action. The actual switching of the content marked as "published" is atomic, but what follows is a slew of asynchronously fired celery tasks that then query the modulestore to re-build their view of the publish data–grades, catalog metadata (CourseOverviews), block transformers for the course outline and mobile APIs, etc. Sometimes those tasks are extremely delayed or fail altogether, which puts us in a weird half-published state where mobile clients see the problem content from version B but are stuck with the outline from version B.

It might be that achieving this goal is unrealistic, and that various applications will always need to run significant post-processing in order to produce the optimized format that they need to do their jobs. But I suspect that at least some of what we're doing is a result of simply having an extremely inefficient data model with origins in the earliest prototype days where we'd load the whole course into an object graph at startup.

## Allow features to be ownable, end-to-end, in a de-coupled manner by allowing applications to hook into the publishing lifecycle.

Courseware has gotten too big for any one small team to truly own. These days, it's developed by various groups that typically own end-to-end features such as "grading", "discussions", or proctored exams.

If you want to implement a major new courseware feature that requires more than simple key-value store queries, there are broadly two strategies you can use for data storage today. The first is to add new field data into the XBlocks themselves, and then process that data into a more queryable form when it's published from Studio to the LMS. The second is to side-step the XBlock field data entirely and store your data in a side-car sort of manner in the LMS.

Both of these approaches have drawbacks. Adding fields into XBlocks means that you're mucking with a large shared ball of mud where you don't necessarily understand the impact of your changes and the backwards compatibility issues you might be introducing. Taking a completely side-car approach makes it easier to develop initially, but introduces many data integrity and lifecycle issues around things like import/export, course re-runs, pushing to multiple instances of Open edX, etc. Trying to bridge this issue later and adapt side-car data to import/export properly can become extremely painful (see edx-val).

## Allow basic correctness checks to happen without edx-platform.

This is a nice to have step for people who author in raw XML files in a git repo and use the import API to push their changes. Validation is often limited to "try to push it up to an instance and see what happens", and error messages are often either unhelpful or unavailable.

## Be convenient and performant for ad hoc querying.

This is a nice to have. Advanced course teams sometimes want to do more serious analysis of their content. Today, that involves various regex incantations and custom scripts that read course content into in-memory object graphs and run various checks on them.

# Approach

Making a package format to












Around 2013, Open edX's course publish lifecycle was fairly straightforward. At a data level, every edited version of a course was represented by an immutable document in MongoDB. The act of publishing amounted to changing the pointer that the LMS used to figure out which version of a course run was published. There might be a slight slowdown as some caches got refreshed, but that was pretty much it.

That gradually changed as Open edX evolved in size, complexity, and performance requirements. The modulestore was in many ways a holdover from the earliest prototype days of Open edX, when courses were natively edited and stored as a large set of XML files, parsed at startup.


# Relation to Other Initiatives

Blockstore

Studio/LMS Separation




# Schema

## Contexts

context_context
- id
- ext_id
- title
- version


## Content

Abstraction of content?  Content -> XBlock

content_item
- id = pk identifier, but varchar probably?
- ext_id = unique key --> could just be problem+block@9e17c7af8dd94039bf7934260c8c6387
- slug = optional, human-readable thingy
- separate external ID so that you can do updates (e.g. re-runs) without
  breaking all the internal foreign key links.
- type = "xblock:v1"
- sub_type = "problem"
- title = "What the Fork?"

- definition = text <-- make this a full text search field
- plain_text = just text for searchability? is that redundant? maybe we want to search by tag?


- context_id ?

content_unit
- id
- ext_id = unique key
- title

content_unit_item
- unit_id
- item_id
- order_num

: unique index on (unit, item, order_num)

content_sequence
- id
- ext_id
- title

content_sequence_unit
- sequence_id
- unit_id
- order_num


should policies reference a context specifically? So you can have more than one
context for a given set of items?





xblock
- item_id    (unique)
- usage_key  (unique)
- definition

# Static assets coudl go in an entirely different database with joins across if
# that's helpful.

resources_file
- id
- ext_id
- mime_type
- file_name
- file_path
- title
- description

resources_file_item
- file_id
- item_id

indexes that go both ways on this one


- hash      ----------> We want this in the final, but it's too easy to screw up in the data manipulation, so compute on publish and not as part of the file format.


* Files
* Modules
* Units

## Sequencing

## Grading

grading_policy
grading_problems


## Scheduling


----

Following a number of casual conversations with various folks on the platform teams at edX, I had an idea




**Represent the structures and content supported by the platform today.**

The format should support everything you can do today in an Open edX course, including more obscure things like parent/child relations in XBlocks, settings overrides on problems imported from content libraries, etc.

## Be open-ended enough to accomodate the different types of content and structures we're looking forward to.

This means both supporting organizational structures that are smaller than courses (e.g. LabXchange-style pathways), as well as having leaf content that are not XBlocks.

## Simplify the publish lifecycle.

When you publish a course today, it doesn't cleanly go from version A to version B in an atomic action. The actual switching of the content marked as "published" is atomic, but what follows is a slew of asynchronously fired celery tasks that then query the modulestore to re-build their view of the publish data–grades, catalog metadata (CourseOverviews), block transformers for the course outline and mobile APIs, etc. Sometimes those tasks are extremely delayed or fail altogether, which puts us in a weird half-published state where mobile clients see the problem content from version B but are stuck with the outline from version B.

It might be that achieving this goal is unrealistic, and that various applications will always need to run significant post-processing in order to produce the optimized format that they need to do their jobs. But I suspect that at least some of what we're doing is a result of simply having an extremely inefficient data model with origins in the earliest prototype days where we'd load the whole course into an object graph at startup.

## Allow features to be ownable, end-to-end, in a de-coupled manner by allowing applications to hook into the publishing lifecycle.

Courseware has gotten too big for any one small team to truly own. These days, it's developed by various groups that typically own end-to-end features such as "grading", "discussions", or proctored exams.

If you want to implement a major new courseware feature that requires more than simple key-value store queries, there are broadly two strategies you can use for data storage today. The first is to add new field data into the XBlocks themselves, and then process that data into a more queryable form when it's published from Studio to the LMS. The second is to side-step the XBlock field data entirely and store your data in a side-car sort of manner in the LMS.

Both of these approaches have drawbacks. Adding fields into XBlocks means that you're mucking with a large shared ball of mud where you don't necessarily understand the impact of your changes and the backwards compatibility issues you might be introducing. Taking a completely side-car approach makes it easier to develop initially, but introduces many data integrity and lifecycle issues around things like import/export, course re-runs, pushing to multiple instances of Open edX, etc. Trying to bridge this issue later and adapt side-car data to import/export properly can become extremely painful (see edx-val).

## Allow basic correctness checks to happen without edx-platform.

This is a nice to have step for people who author in raw XML files in a git repo and use the import API to push their changes. Validation is often limited to "try to push it up to an instance and see what happens", and error messages are often either unhelpful or unavailable.

## Be convenient and performant for ad hoc querying.

This is a nice to have. Advanced course teams sometimes want to do more serious analysis of their content. Today, that involves various regex incantations and custom scripts that read course content into in-memory object graphs and run various checks on them.



# Questions

What about Blockstore?

How does this relate to architectural divisions between Studio and the LMS?

Does that break OLX compatibility?

Multi-course capable format? --> This would make it hard to have one per
published course, but might give the ability to have the ability to reference
multiple libraries that it comes from.

Oh crap, we might be able to encode MULTIPLE RUNS at once. That's... huh...

You know, we actually have to encode MULTIPLE VERSIONS of MULTIPLE CONTEXTS at
once, because a course run can have content from different versions of the same
library.

Time stamps? But those are kind of weird in the auto-generated case. And maybe
untrustworthy?
