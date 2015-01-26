/*
 *  Copyright (c) 2014 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree.
 */


/* exported Call */
'use strict';

/*
 * The analytics object is used to send up client-side logging
 * information.
 * @param {string} URL to the room server.
 * @constructor
 */
var Analytics = function(roomServer) {
  /* @private {string} Room server URL. */
  this.analyticsPath_ = roomServer + '/a/';
};

/*
 * Report an event.
 *
 * @param {string} event The event string to record.
 * @param {string=} roomId The current room ID.
 */
Analytics.prototype.reportEvent = function(event, roomId) {
  eventObj = {
    'event_name': event,
    'event_time_ms': new Date().getTime()
  };
  if (roomId) {
    event['room_id'] = roomId;
  }
  trace('Reporting event: ' + eventObj);
  this.sendEventRequest_(eventObj);
};

/*
 * Send an event object to the server.
 * @param {{type}}
 */
Analytics.prototype.sendEventRequest_ = function(eventObj) {
  request = {
    'type': 'event',
    'request_time_ms': new Date().getTime(),
    'content': JSON.stringify(eventObj)
  };
  sendAsyncUrlRequest('POST', this.analyticsPath_, JSON.stringify(request)).
      then(function() {
    trace('Successfully sent event.');
  }.bind(this), function(error) {
    trace('Failed to send event request: ' + error.message);
  }.bind(this));
};
