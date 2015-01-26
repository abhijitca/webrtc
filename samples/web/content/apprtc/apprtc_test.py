# Copyright 2014 Google Inc. All Rights Reserved.

import json
import logging
import time
import unittest
import webtest

from google.appengine.api import memcache
from google.appengine.ext import testbed

import apprtc
import analytics
import constants
from test_util import CapturingFunction, ReplaceFunction


class AppRtcUnitTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()

    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()

  def tearDown(self):
    self.testbed.deactivate()

  def testGenerateRandomGeneratesStringOfRightLength(self):
    self.assertEqual(17, len(apprtc.generate_random(17)))
    self.assertEqual(23, len(apprtc.generate_random(23)))


class AppRtcPageHandlerTest(unittest.TestCase):
  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()

    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()

    # Next, declare which service stubs you want to use.
    self.testbed.init_memcache_stub()

    self.test_app = webtest.TestApp(apprtc.app)

    self.time_now = time.time()

    # Fake out event reporting and capture arguments.
    self.reportEventReplacement = ReplaceFunction(
        analytics,
        'report_event',
        CapturingFunction())

    self.analyticsPageNowReplacement = ReplaceFunction(
        apprtc.AnalyticsPage,
        '_time',
        self.fake_time);

  def tearDown(self):
    self.testbed.deactivate()
    del self.reportEventReplacement
    del self.analyticsPageNowReplacement

  def fake_time(self):
    return self.time_now

  def makeGetRequest(self, path):
    # PhantomJS uses WebKit, so Safari is closest to the thruth.
    return self.test_app.get(path, headers={'User-Agent': 'Safari'})

  def makePostRequest(self, path, body='', expect_errors=False):
    return self.test_app.post(path, body, headers={'User-Agent': 'Safari'},
                              expect_errors=expect_errors)

  def verifyJoinSuccessResponse(self, response, is_initiator, room_id):
    self.assertEqual(response.status_int, 200)
    response_json = json.loads(response.body)

    self.assertEqual('SUCCESS', response_json['result'])
    params = response_json['params']
    caller_id = params['client_id']
    self.assertTrue(len(caller_id) > 0)
    self.assertEqual(json.dumps(is_initiator), params['is_initiator'])
    self.assertEqual(room_id, params['room_id'])
    self.assertEqual([], params['error_messages'])
    return caller_id

  def testConnectingWithoutRoomIdServesIndex(self):
    response = self.makeGetRequest('/')
    self.assertEqual(response.status_int, 200)
    self.assertNotRegexpMatches(response.body, 'roomId:')

  def testConnectingWithRoomIdServesIndex(self):
    response = self.makeGetRequest('/r/testRoom')
    self.assertEqual(response.status_int, 200)
    self.assertRegexpMatches(response.body, 'roomId: \'testRoom\'')

  def testJoinAndLeave(self):
    room_id = 'foo'
    # Join the caller.
    response = self.makePostRequest('/join/' + room_id)
    caller_id = self.verifyJoinSuccessResponse(response, True, room_id)

    # Join the callee.
    response = self.makePostRequest('/join/' + room_id)
    callee_id = self.verifyJoinSuccessResponse(response, False, room_id)

    # The third user will get an error.
    response = self.makePostRequest('/join/' + room_id)
    self.assertEqual(response.status_int, 200)
    response_json = json.loads(response.body)
    self.assertEqual('FULL', response_json['result'])

    # The caller and the callee leave.
    self.makePostRequest('/leave/' + room_id + '/' + caller_id)
    self.makePostRequest('/leave/' + room_id + '/' + callee_id)
    # Another user becomes the new caller.
    response = self.makePostRequest('/join/' + room_id)
    caller_id = self.verifyJoinSuccessResponse(response, True, room_id)
    self.makePostRequest('/leave/' + room_id + '/' + caller_id)

  def testCallerMessagesForwardedToCallee(self):
    room_id = 'foo'
    # Join the caller.
    response = self.makePostRequest('/join/' + room_id)
    caller_id = self.verifyJoinSuccessResponse(response, True, room_id)
    # Caller's messages should be saved.
    messages = ['1', '2', '3']
    path = '/message/' + room_id + '/' + caller_id
    for msg in messages:
      response = self.makePostRequest(path, msg)
      response_json = json.loads(response.body)
      self.assertEqual('SUCCESS', response_json['result'])

    response = self.makePostRequest('/join/' + room_id)
    callee_id = self.verifyJoinSuccessResponse(response, False, room_id)
    received_msgs = json.loads(response.body)['params']['messages']
    self.assertEqual(messages, received_msgs)

    self.makePostRequest('/leave/' + room_id + '/' + caller_id)
    self.makePostRequest('/leave/' + room_id + '/' + callee_id)

  def testAnalyticsPage(self):
    # self.time_ms will be the time the request is recieved by AppRTC
    self.time_now = 11.0
    request_time_ms = 10.0 * 1000
    event_time_ms = 8.0 * 1000
    # The client time (request_time) is one second behind the server
    # time (self.time_now) so the event time, as the server sees it,
    # should be one second ahead of the actual event time recorded by
    # the client.
    event_time_server_ms = 9.0 * 1000

    room_id = 'foo'
    event_type = constants.EventType.ICE_CONNECTION_STATE_CONNECTED

    # Test with all optional attributes.
    event = {
        'event_type': event_type,
        'event_time_ms': event_time_ms,
        'room_id': room_id,
        }

    request = {
        'type': 'event',
        'request_time_ms': request_time_ms,
        'content': json.dumps(event)
        }

    response = self.makePostRequest('/a/', body=json.dumps(request))
    response_body = json.loads(response.body)

    self.assertEqual(constants.RESPONSE_SUCCESS, response_body['result'])

    expectedArgs = (event_type, room_id, event_time_server_ms, event_time_ms)

    self.assertEqual(expectedArgs, analytics.report_event.lastArgs)

    # Test without optional attributes.
    event = {
        'event_type': event_type,
        'event_time_ms': event_time_ms,
        }

    request = {
        'type': 'event',
        'request_time_ms': request_time_ms,
        'content': json.dumps(event)
        }

    response = self.makePostRequest('/a/', body=json.dumps(request))
    response_body = json.loads(response.body)

    self.assertEqual(constants.RESPONSE_SUCCESS, response_body['result'])

    expectedArgs = (event_type, None, event_time_server_ms, event_time_ms)

    self.assertEqual(expectedArgs, analytics.report_event.lastArgs)


  def testAnalyticsPageFail(self):
    # Test empty body.
    response = self.makePostRequest('/a/', expect_errors=True)
    response_body = json.loads(response.body)
    self.assertEqual(400, response.status_code)
    self.assertEqual(constants.RESPONSE_ERROR, response_body['result'])

    # Test missing individual required attributes.
    room_id = 'foo'
    event_type = constants.EventType.ICE_CONNECTION_STATE_CONNECTED
    time_ms = 1337

    # Fully populated event and request.
    event = {
        'event_type': event_type,
        'event_time_ms': time_ms,
        'room_id': room_id,
        }

    request = {
        'type': 'event',
        'request_time_ms': time_ms,
        'content': json.dumps(event)
        }

    # Unknown type of analytics request
    request_unknown_type = request.copy()
    request_unknown_type['type'] = 'crazy_brains'
    response = self.makePostRequest(
        '/a/', body=json.dumps(request_unknown_type), expect_errors=True)
    response_body = json.loads(response.body)
    self.assertEqual(400, response.status_code)
    self.assertEqual(constants.RESPONSE_ERROR, response_body['result'])

    # Missing required members of the request.
    for member in ('type', 'request_time_ms'):
      tmp_request = request.copy()
      del tmp_request[member]
      response = self.makePostRequest(
          '/a/', body=json.dumps(tmp_request), expect_errors=True)
      response_body = json.loads(response.body)
      self.assertEqual(400, response.status_code)
      self.assertEqual(constants.RESPONSE_ERROR, response_body['result'])


    # Missing required members of the event.
    for member in ('event_type', 'event_time_ms'):
      tmp_request = request.copy()
      tmp_event = event.copy()
      del tmp_event[member]
      tmp_request['content'] = json.dumps(tmp_event)
      response = self.makePostRequest(
          '/a/', body=json.dumps(tmp_request), expect_errors=True)
      response_body = json.loads(response.body)
      self.assertEqual(400, response.status_code)
      self.assertEqual(constants.RESPONSE_ERROR, response_body['result'])



if __name__ == '__main__':
  unittest.main()
