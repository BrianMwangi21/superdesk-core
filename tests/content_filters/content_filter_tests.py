# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import json

from eve.utils import ParsedRequest

from apps.content_filters.content_filter.content_filter_service import ContentFilterService
from apps.prepopulate.app_populate import AppPopulateCommand
from superdesk import get_backend, get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.publish import SubscribersService
from superdesk.tests import TestCase


class ContentFilterTests(TestCase):
    def setUp(self):
        self.req = ParsedRequest()
        with self.app.test_request_context(self.app.config.get("URL_PREFIX")):
            self.f = ContentFilterService(datasource="content_filters", backend=get_backend())
            self.s = SubscribersService(datasource="subscribers", backend=get_backend())

            self.articles = [
                {"_id": "1", "urgency": 1, "headline": "story", "state": "fetched", "task": {"desk": 1}},
                {"_id": "2", "headline": "prtorque", "state": "fetched", "task": {"desk": 1}},
                {"_id": "3", "urgency": 3, "headline": "creator", "state": "fetched", "task": {"desk": 1}},
                {"_id": "4", "urgency": 4, "state": "fetched", "task": {"desk": 1}},
                {"_id": "5", "urgency": 2, "state": "fetched", "task": {"desk": 1}},
                {"_id": "6", "state": "fetched", "task": {"desk": 1}},
                {"_id": "7", "subject": [{"scheme": "my_vocabulary", "qcode": "MV:01"}], "task": {"desk": 1}},
                {"_id": "8", "extra": {"custom_text": "my text"}, "task": {"desk": 1}},
            ]
            self.app.data.insert("archive", self.articles)

            self.app.data.insert(
                "vocabularies",
                [
                    {
                        "_id": "my_vocabulary",
                        "display_name": "My Vocabulary",
                        "type": "manageable",
                        "field_type": None,
                        "schema": {"name": {}, "qcode": {}, "parent": {}},
                        "items": [{"name": "option 1", "qcode": "MV:01", "is_active": True}],
                    },
                    {"_id": "custom_text", "display_name": "Custom Text", "type": "manageable", "field_type": "text"},
                ],
            )

            self.app.data.insert(
                "filter_conditions",
                [{"_id": 1, "field": "headline", "operator": "like", "value": "tor", "name": "test-1"}],
            )
            self.app.data.insert(
                "filter_conditions", [{"_id": 2, "field": "urgency", "operator": "in", "value": "2", "name": "test-2"}]
            )
            self.app.data.insert(
                "filter_conditions",
                [{"_id": 3, "field": "headline", "operator": "endswith", "value": "tor", "name": "test-3"}],
            )
            self.app.data.insert(
                "filter_conditions",
                [{"_id": 4, "field": "urgency", "operator": "in", "value": "2,3,4", "name": "test-4"}],
            )
            self.app.data.insert(
                "filter_conditions",
                [{"_id": 5, "field": "headline", "operator": "startswith", "value": "sto", "name": "test-5"}],
            )
            self.app.data.insert(
                "filter_conditions",
                [{"_id": 6, "field": "my_vocabulary", "operator": "in", "value": "MV:01", "name": "test-6"}],
            )
            self.app.data.insert(
                "filter_conditions",
                [{"_id": 7, "field": "custom_text", "operator": "eq", "value": "my text", "name": "test-7"}],
            )

            self.app.data.insert(
                "content_filters", [{"_id": 1, "content_filter": [{"expression": {"fc": [1]}}], "name": "soccer-only"}]
            )

            self.app.data.insert(
                "content_filters",
                [{"_id": 2, "content_filter": [{"expression": {"fc": [4, 3]}}], "name": "soccer-only2"}],
            )

            self.app.data.insert(
                "content_filters",
                [{"_id": 3, "content_filter": [{"expression": {"pf": [1], "fc": [2]}}], "name": "soccer-only3"}],
            )

            self.app.data.insert(
                "content_filters",
                [
                    {
                        "_id": 4,
                        "content_filter": [{"expression": {"fc": [3]}}, {"expression": {"fc": [5]}}],
                        "name": "soccer-only4",
                    }
                ],
            )

            self.app.data.insert(
                "content_filters",
                [{"_id": 5, "content_filter": [{"expression": {"fc": [6]}}], "name": "my-vocabulary"}],
            )

            self.app.data.insert(
                "content_filters", [{"_id": 6, "content_filter": [{"expression": {"fc": [7]}}], "name": "custom-text"}]
            )

            self.app.data.insert(
                "products", [{"_id": 1, "content_filter": {"filter_id": 3, "filter_type": "blocking"}, "name": "p-1"}]
            )

            self.app.data.insert(
                "products", [{"_id": 2, "content_filter": {"filter_id": 1, "filter_type": "blocking"}, "name": "p-2"}]
            )

            self.app.data.insert("subscribers", [{"_id": 1, "products": [1], "name": "sub1"}])
            self.app.data.insert("subscribers", [{"_id": 2, "products": [2], "name": "sub2"}])

            self.app.data.insert(
                "routing_schemes",
                [
                    {
                        "_id": 1,
                        "name": "routing_scheme_1",
                        "rules": [
                            {
                                "filter": 4,
                                "name": "routing_rule_4",
                                "schedule": {
                                    "day_of_week": ["MON"],
                                    "hour_of_day_from": "0000",
                                    "hour_of_day_to": "2355",
                                },
                                "actions": {"fetch": [], "publish": [], "exit": False},
                            }
                        ],
                    }
                ],
            )


class RetrievingDataTests(ContentFilterTests):
    def test_build_mongo_query_using_like_filter_single_fc(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(3, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)

    def test_build_mongo_query_using_like_filter_single_pf(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(3, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_filter_condition(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(4, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("5" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_pf(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(4, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("5" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_filter_condition2(self):
        doc = {"content_filter": [{"expression": {"fc": [3, 4]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_pf2(self):
        doc = {"content_filter": [{"expression": {"pf": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_condition3(self):
        doc = {"content_filter": [{"expression": {"fc": [3, 4]}}, {"expression": {"fc": [1, 2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_pf3(self):
        doc = {"content_filter": [{"expression": {"pf": [2]}}, {"expression": {"pf": [1], "fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = self.f.build_mongo_query(doc)
            docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_single_filter_condition(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(3, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_single_content_filter(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(3, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_filter_condition(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(4, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)
            self.assertTrue("5" in doc_ids)

    def test_build_mongo_query_using_like_filter_multi_content_filter(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(4, docs.count())
            self.assertTrue("1" in doc_ids)
            self.assertTrue("2" in doc_ids)
            self.assertTrue("3" in doc_ids)
            self.assertTrue("5" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_filter_condition2(self):
        doc = {"content_filter": [{"expression": {"fc": [3, 4]}}, {"expression": {"fc": [1, 2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_content_filter2(self):
        doc = {
            "content_filter": [{"expression": {"fc": [4, 3]}}, {"expression": {"pf": [1], "fc": [2]}}],
            "name": "pf-1",
        }
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_content_filter3(self):
        doc = {"content_filter": [{"expression": {"pf": [2]}}, {"expression": {"pf": [1], "fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_content_filter4(self):
        doc = {"content_filter": [{"expression": {"pf": [2]}}, {"expression": {"pf": [3]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)

    def test_build_elastic_query_using_like_filter_multi_content_filter5(self):
        doc = {"content_filter": [{"expression": {"pf": [4], "fc": [4]}}], "name": "pf-1"}
        with self.app.app_context():
            query = {"query": {"filtered": {"query": self.f._get_elastic_query(doc)}}}
            self.req.args = {"source": json.dumps(query)}
            docs = get_resource_service("archive").get(req=self.req, lookup=None)
            doc_ids = [d["_id"] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue("3" in doc_ids)


class FilteringDataTests(ContentFilterTests):
    def test_does_match_returns_true_for_nonexisting_filter(self):
        for article in self.articles:
            self.assertTrue(self.f.does_match(None, article))

    def test_does_match_custom_vocabularies(self):
        doc1 = {"content_filter": [{"expression": {"fc": [6]}}], "name": "mv-1"}
        doc2 = {"content_filter": [{"expression": {"fc": [7]}}], "name": "ct-1"}
        with self.app.app_context():
            self.assertTrue(self.f.does_match(doc1, self.articles[6]))
            self.assertTrue(self.f.does_match(doc2, self.articles[7]))

    def test_does_match_using_like_filter_single_fc(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertTrue(self.f.does_match(doc, self.articles[0]))
            self.assertTrue(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_single_pf(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertTrue(self.f.does_match(doc, self.articles[0]))
            self.assertTrue(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_fc(self):
        doc = {"content_filter": [{"expression": {"fc": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertTrue(self.f.does_match(doc, self.articles[0]))
            self.assertTrue(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertTrue(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_pf(self):
        doc = {"content_filter": [{"expression": {"pf": [1]}}, {"expression": {"fc": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertTrue(self.f.does_match(doc, self.articles[0]))
            self.assertTrue(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertTrue(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_fc2(self):
        doc = {"content_filter": [{"expression": {"fc": [3, 4]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertFalse(self.f.does_match(doc, self.articles[0]))
            self.assertFalse(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_pf2(self):
        doc = {"content_filter": [{"expression": {"pf": [2]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertFalse(self.f.does_match(doc, self.articles[0]))
            self.assertFalse(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_fc3(self):
        doc = {"content_filter": [{"expression": {"fc": [3, 4]}}, {"expression": {"fc": [1, 2]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertFalse(self.f.does_match(doc, self.articles[0]))
            self.assertFalse(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_does_match_using_like_filter_multi_pf3(self):
        doc = {"content_filter": [{"expression": {"pf": [4], "fc": [4]}}], "name": "pf-1"}
        with self.app.app_context():
            self.assertFalse(self.f.does_match(doc, self.articles[0]))
            self.assertFalse(self.f.does_match(doc, self.articles[1]))
            self.assertTrue(self.f.does_match(doc, self.articles[2]))
            self.assertFalse(self.f.does_match(doc, self.articles[3]))
            self.assertFalse(self.f.does_match(doc, self.articles[4]))
            self.assertFalse(self.f.does_match(doc, self.articles[5]))

    def test_if_pf_is_used(self):
        with self.app.app_context():
            self.assertTrue(self.f._get_content_filters_by_content_filter(1).count() == 1)
            self.assertTrue(self.f._get_content_filters_by_content_filter(4).count() == 0)

    def test_if_fc_is_used(self):
        with self.app.app_context():
            self.assertTrue(len(self.f.get_content_filters_by_filter_condition(1)) == 2)
            self.assertTrue(len(self.f.get_content_filters_by_filter_condition(3)) == 2)
            self.assertTrue(len(self.f.get_content_filters_by_filter_condition(2)) == 1)

    def test_get_subscribers_by_filter_condition(self):
        filter_condition1 = {"field": "urgency", "operator": "in", "value": "2"}
        filter_condition2 = {"field": "urgency", "operator": "in", "value": "1"}
        filter_condition3 = {"field": "headline", "operator": "like", "value": "tor"}
        filter_condition4 = {"field": "urgency", "operator": "nin", "value": "3"}

        with self.app.app_context():
            cmd = AppPopulateCommand()
            filename = os.path.join(
                os.path.abspath(os.path.dirname("apps/prepopulate/data_init/vocabularies.json")), "vocabularies.json"
            )
            cmd.run(filename)
            r1 = self.s._get_subscribers_by_filter_condition(filter_condition1)
            r2 = self.s._get_subscribers_by_filter_condition(filter_condition2)
            r3 = self.s._get_subscribers_by_filter_condition(filter_condition3)
            r4 = self.s._get_subscribers_by_filter_condition(filter_condition4)
            self.assertTrue(len(r1[0]["selected_subscribers"]) == 1)
            self.assertTrue(len(r2[0]["selected_subscribers"]) == 0)
            self.assertTrue(len(r3[0]["selected_subscribers"]) == 2)
            self.assertTrue(len(r4[0]["selected_subscribers"]) == 1)

    def test_does_match_return_with_caching_mechanism(self):
        self.app.data.insert(
            "filter_conditions",
            [
                {
                    "_id": 621,
                    "operator": "in",
                    "field": "my_vocabulary",
                    "value": "BIN/ALG",
                    "name": "Bin/alg filter_c",
                },
            ],
        )
        content_filter = [
            {
                "_id": 1234,
                "name": "Bin/ALG Filter",
                "content_filter": [{"expression": {"fc": [621]}}],
            },
        ]
        self.app.data.insert("content_filters", content_filter)

        item = {
            "_id": "urn:newsml:localhost:5000:2019-12-10T14:43:46.224107:d13ac5ae-7f43-4b7f-89a5-2c6835389564",
            "guid": "urn:newsml:localhost:5000:2019-12-10T14:43:46.224107:d13ac5ae-7f43-4b7f-89a5-2c6835389564",
            "subject": [
                {
                    "name": "BIN/ALG",
                    "qcode": "BIN/ALG",
                    "parent": "BIN",
                    "scheme": "my_vocabulary",
                },
            ],
        }

        response = self.f.does_match(content_filter=content_filter[0], article=item)
        self.assertTrue(response)

        # Modified Item data
        item["subject"] = [
            {
                "name": "BIN/ECO",
                "qcode": "BIN/ECO",
                "parent": "BIN",
                "scheme": "my_vocabulary",
            },
        ]

        # Default cache is True
        response = self.f.does_match(content_filter=content_filter[0], article=item)
        self.assertTrue(response)

        # with cache = False
        response = self.f.does_match(content_filter=content_filter[0], article=item, cache=False)
        self.assertFalse(response)


class DeleteMethodTestCase(ContentFilterTests):
    """Tests for the delete() method."""

    def test_raises_error_if_filter_referenced_by_subscribers(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            self.f.delete({"_id": 1})

        self.assertEqual(ctx.exception.status_code, 400)  # bad request error

    def test_raises_error_if_filter_referenced_by_routing_rules(self):
        with self.assertRaises(SuperdeskApiError) as ctx:
            self.f.delete({"_id": 4})

        self.assertEqual(ctx.exception.status_code, 400)  # bad request error
