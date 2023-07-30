=====
Dope Django Notes
=====

Note mixin for Django.

Quick start
-----------

1. Add "dd_easy_views" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...,
        "dd_notes",
    ]

2. To use the Note mixin in your project, do the followings::

    from dd_notes.mixins import NoteViewMixin
    from django.views import generic

    class ModelListView(generic.ListView, NoteViewMixin):
        ...

    and include the template by including the template tag::
        Must specify the table_id and lookup_field_index

        The table ID field is... the "id" of your HTML table.

        The lookup_field_index is the index of the field in your table that you want to use to look up the note. This will be used in URL creation, currently only support PK.

        {% include "dd_notes/note.html" table_id=<your_table_id> lookup_field_index=0 %}