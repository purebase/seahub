# Copyright (c) 2012-2016 Seafile Ltd.
import os
from django.db import models
from django.core.urlresolvers import reverse

from seahub.base.fields import LowerCaseCharField
from seahub.base.templatetags.seahub_tags import email2nickname, email2contact_email
from seahub.profile.models import Profile
from seahub.utils.timeutils import timestamp_to_isoformat_timestr

import seaserv
from seaserv import seafile_api


########## manager
class TagsManager(models.Manager):
    def get_all_tag_name(self):
        return [tag.name for tag in super(TagsManager, self).all()]

    def get_or_create_tag(self, tagname):
        try:
            tag = super(TagsManager, self).get(name=tagname)
            return tag
        except self.model.DoesNotExist:
            tag = self.model(name=tagname)
            tag.save()
            return tag

class VersionTagsManager(models.Manager):
    def get_one_version_tag(self, repo_id, commit_id, tag_name):
        try:
            return super(VersionTagsManager, self).get(
                    repo_id=repo_id,
                    version_id=commit_id,
                    tag__name=tag_name)
        except:
            return None

    def get_all_version_tag_by_repo(self, repo_id):
        return super(VersionTagsManager, self).filter(repo_id=repo_id)

    def create_version_tag(self, repo_id, commit_id, tag_name, creator):
        version_tag = self.get_one_version_tag(repo_id, commit_id, tag_name)
        if version_tag:
            return version_tag, False
        else:
            tag = Tags.objects.get_or_create_tag(tag_name)
            version_tag = self.model(repo_id=repo_id, version_id=commit_id, tag=tag)
            version_tag.save()
            return version_tag, True

    def delete_version_tag(self, repo_id, commit_id, tag_name):
        version_tag = self.get_one_version_tag(repo_id, commit_id, tag_name)
        if not version_tag:
            return False
        else:
            version_tag.delete()
            return True

########## models
class Tags(models.Model):
    name = models.CharField(max_length=255, unique=True)
    objects = TagsManager()

class VersionTags(models.Model):
    repo_id = models.CharField(max_length=36, db_index=True)
    path = models.TextField(default='/')
    version_id = models.CharField(max_length=255, db_index=True)
    tag = models.ForeignKey("Tags", on_delete=models.CASCADE)
    username = LowerCaseCharField(max_length=255, db_index=True)
    objects = VersionTagsManager()

    def to_dict(self):
        repo = seafile_api.get_repo(self.repo_id)
        commit = seaserv.get_commit(repo.id, repo.version, self.version_id)
        email = commit.creator_name
        return  {"tag":self.tag.name,
                 "creator": self.username,
                 "snaphot": {
                     "repo_id": self.repo_id,
                     "commit_id": self.version_id,
                     "email": email,
                     "name": email2nickname(email),
                     "contact_email": email2contact_email(email),
                     "time": timestamp_to_isoformat_timestr(commit.ctime),
                     "description": commit.desc,
                     "link": reverse("repo_history_view", args=[self.repo_id])+"?commit_id=%s"%self.version_id
                     }}
