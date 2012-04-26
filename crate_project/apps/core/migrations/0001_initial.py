# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserAgent'
        db.create_table('core_useragent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('raw', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('short', self.gf('django.db.models.fields.CharField')(max_length=150)),
        ))
        db.send_create_signal('core', ['UserAgent'])

    def backwards(self, orm):
        # Deleting model 'UserAgent'
        db.delete_table('core_useragent')

    models = {
        'core.useragent': {
            'Meta': {'object_name': 'UserAgent'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'short': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        }
    }

    complete_apps = ['core']