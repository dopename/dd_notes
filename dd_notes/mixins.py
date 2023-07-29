import datetime
import json

from django.http import JsonResponse

from django import forms
from django.views.generic import ListView

from django.contrib.auth import get_user_model
from django.db.models.fields.reverse_related import ManyToOneRel
from django.db import models

from django.contrib.postgres.fields import ArrayField


def get_related_model_by_name(model, names: list =[]):
    """
    Given a model, return the name of the related model
    """
    for name in names:
        try:
            model._meta.get_field(name)
        except:
            continue
        else:
            try:
                return model._meta.get_field(name).related_model
            except:
                pass
    return None

def parse_notes_model_fields(note_model, related_model):
    text_names = ['text', 'note', 'description', 'content']
    text_field = None
    for name in text_names:
        try:
            note_model._meta.get_field(name)
        except:
            continue
        else:
            text_field = name

    assert text_field, "Text field not found in Note model"

    timestamp_field = None
    user_field = None
    related_field = None

    for field in note_model._meta.get_fields():
        if field.get_internal_type() == 'DateTimeField' and not timestamp_field:
            timestamp_field = field.name
        elif field.get_internal_type() == 'ForeignKey' and field.related_model == get_user_model() and not user_field:
            user_field = field.name
        elif type(field) == ManyToOneRel and field.related_model == related_model and not related_field:
            related_field = field.name

        if user_field and timestamp_field and related_field:
            break

    if None in [timestamp_field, user_field, related_field]:
        raise Exception('Names are not valid for the Note model')

    return {
        'text_field': text_field,
        'timestamp_field': timestamp_field,
        'user_field': user_field,
        'related_field': related_field
    }


class NoteHelper:

    def __init__(self, **kwargs):
        pass

class NoteViewMixin:
    """
    Need to do some setup on the inheriting view, namely need:
    :note_form_class: The form class to use for the notes
    :note_get_param: The GET parameter to use to get the notes
    :note_relation_name: The name of relating model to the Note model
    :model_lookup_field: The lookup field for the related object
    :note_user_field: The field on the Note model for the related account/user
    :note_model: The Note model
    :note_timestamp_field_name: The field on the Note model for the timestamp

    """
    MODES = ['model', 'text', 'json', 'list']

    def __init__(self, **kwargs):
        required_variables = [
            'note_form_class', 'note_get_param', 'note_relation_name',
            'model_lookup_field', 'note_user_field', 'note_model',
            'note_timestamp_field_name'
        ]

        # Allow to set variables on call
        for key, value in kwargs.items():
            if key in required_variables:
                setattr(self, key, value)

        if 'note_model' not in kwargs:
            self.note_model = get_related_model_by_name(self.model, ['notes'])
        # Notes field will only be used when there is no note_model
        self.notes_field = None
        self.mode = 'model'

        if not self.note_model:
            # Sounds like notes is just a JSON or text field
            try:
                self.notes_field = self.model._meta.get_field('notes')
            except Exception as e:
                raise e
            else:
                if not getattr(self, 'note_form_class', None):
                    class NoteForm(forms.Form):
                        text = forms.CharField()

                    self.note_form_class = NoteForm

                if type(self.notes_field) == models.JSONField:
                    self.mode = 'json'
                elif type(self.notes_field) == models.TextField:
                    self.mode = 'text'
                elif type(self.notes_field) == ArrayField:
                    # Not planning on handling this for now
                    self.mode = 'list'
                else:
                    raise Exception("Must be a big CharField, I'll think about letting them in in the future.")
        else:

            # small function to cleanly handle set-if-not-passed logic
            def get_or_set(property, value):
                if not hasattr(self, property):
                    setattr(self, property, value)
                return getattr(self, property)
            
            fields = parse_notes_model_fields(self.note_model, self.model)
            # Will need to figure out get_param and related_object_lookup later.. maybe by looking at urlpatterns?
            self.note_get_param = get_or_set('note_get_param', 'pk')
            self.note_relation_name = get_or_set('note_relation_name', fields['related_field'])
            self.model_lookup_field = get_or_set('model_lookup_field', 'pk')
            self.note_user_field = get_or_set('note_user_field', fields['user_field'])
            self.note_text_field = get_or_set('note_text_field', fields['text_field'])
            self.note_timestamp_field = get_or_set('note_timestamp_field', fields['timestamp_field'])

            if not hasattr(self, 'note_form_class'):
                class NoteForm(forms.ModelForm):
                    class Meta:
                        model = self.note_model
                        fields = [self.note_text_field]

                self.note_form_class = NoteForm

            for variable in required_variables:
                if not hasattr(self, variable):
                    raise Exception(f"NoteViewMixin requires {variable} to be set.")
            
        super().__init__()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.note_form_class()
        return context

    def get(self, request, *args, **kwargs):
        # TODO: can maybe expand this to just passing in any kwargs
        if self.note_get_param not in request.GET:
            return super().get(request, *args, **kwargs)
        
        get_param_id = request.GET.get(self.note_get_param)
        lookup = {self.model_lookup_field: get_param_id}
        
        # Grab the notes for the given model. Need to specify the field lookup in GET
        if not self.notes_field:
            try:
                obj = self.model.objects.prefetch_related(self.note_relation_name).get(**lookup)
            except self.model.DoesNotExist:
                # TODO: allow for custom error handling
                return JsonResponse({}, status=400)
            else:
                # Get the notes, select related for user
                note_list = getattr(obj, self.note_relation_name).select_related(self.note_user_field).all()
                # Structure the notes into the desired JSON format
                notes = [
                    self.format_note_json(x) for x in note_list
                ]
        else:
            # Json/Array Field handling
            try:
                obj = self.model.objets.get(**lookup)
            except self.model.DoesNotExist:
                return JsonResponse({}, status=400)
            else:
                notes = getattr(obj, self.notes_field.name)

        return JsonResponse({'notes': notes}, status=200)


    def format_note_json(self, note):
        note_json = {
            'user': str(getattr(note, self.note_user_field)),
            'timestamp': getattr(note, self.note_timestamp_field_name).astimezone().strftime("%m/%d/%Y, %I:%M %p"),
            'text': getattr(note, self.note_text_field)
        }
        return note_json
    
    def create_note_field_json(self, note):
        # note_field is the term used for flat text storage
        note_json = {
            'user': self.request.user.username,
            'timestamp': datetime.datetime.now().astimezone().strftime("%m/%d/%Y, %I:%M %p"),
            'text': note
        }
        return note_json

    def post(self, request, *args, **kwargs):
        form = self.note_form_class(request.POST)

        if self.notes_field:
            # This is a text field
            if form.is_valid():
                obj = self.get_object()
                notes = getattr(obj, self.notes_field.name)
                # Essentially for Array/Json field we want to use array. Just json.load if its text
                if type(notes) == str:
                    notes = json.loads(notes)
                elif type(notes) != list:
                    notes = []

                form_text = form.cleaned_data['text']
                notes.append(self.create_note_field_json(form_text))

                setattr(obj, self.notes_field.name, notes)
                obj.save()
                return JsonResponse({'notes':notes}, status=200)
            return JsonResponse({'errors':form.errors}, status=400)

        if form.is_valid():
            obj = form.save(commit=False)
            if self.note_user_field:
                setattr(obj, self.note_user_field, request.user)
                obj.save()

            obj.refresh_from_db()

            note = self.note_model.objects.get(id=obj.id)
            serialized_note = self.format_note_json(note)
            return JsonResponse({'notes':[serialized_note]}, status=200)
        return JsonResponse({'errors':form.errors}, status=400)