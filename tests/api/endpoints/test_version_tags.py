import os
import json

from django.core.urlresolvers import reverse

from seahub.test_utils import BaseTestCase
import seaserv
from seaserv import seafile_api


class VersionTagsTest(BaseTestCase):
    def setUp(self):
        self.login_as(self.user)

    def test_get_version_tags(self):
        self.tag_name = "test_tag_name"
        self.repo = seafile_api.get_repo(self.create_repo(
            name="test_repo",
            desc="",
            username=self.user.username,
            passwd=None
        ))
        self.commit = seafile_api.get_commit_list(self.repo.id, -1, -1)

        self.url = reverse("api-v2.1-version-tags", args=[self.repo.id])
        c_resp = self.client.post(self.url, {
            "commit_id": self.commit[0].id,
            "tag_name": self.tag_name,
        })
        assert c_resp.status_code in [200, 201]

        g_resp = self.client.get(self.url, args=[self.repo.id])
        assert g_resp.status_code == 200
        assert self.tag_name in [tag["tag"] for tag in g_resp.data]

        self.d_url = reverse("api-v2.1-version-tag", args=[self.repo.id, self.tag_name])
        self.d_url += "?commit_id=" + str(self.commit[0].id)
        d_resp = self.client.delete(self.d_url)
        assert d_resp.status_code in [200, 202]

        g_resp = self.client.get(self.url, args=[self.repo.id])
        assert g_resp.status_code == 200
        assert self.tag_name not in [tag["tag"] for tag in g_resp.data]
