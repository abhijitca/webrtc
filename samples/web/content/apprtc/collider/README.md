# Collider

A websocket-based signaling server in Go.

## Building

1. Install the Go tools and workspaces as documented at http://golang.org/doc/install and http://golang.org/doc/code.html

2. Build and install collider,

        go install github.com/googlechrome/webrtc/samples/web/content/apprtc/collider

## Running

    $GOPATH/bin/collider -port=8089 -tls=true

## Testing

    go test github.com/googlechrome/webrtc/samples/web/content/apprtc/collider/collider

