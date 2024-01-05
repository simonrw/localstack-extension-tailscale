package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"

	"tailscale.com/tsnet"
)

func main() {
	// configuration
	port := os.Getenv("TSPROXY_PORT")
	if port == "" {
		port = "1992"
	}
	upstreamURL := os.Getenv("TSPROXY_UPSTREAM_URL")
	if upstreamURL == "" {
		upstreamURL = "http://localstack:4566"
	}

	// setup tailscale
	s := new(tsnet.Server)
	s.Hostname = "lstsproxy"
	s.Ephemeral = true
	defer s.Close()

	listenAddr := fmt.Sprintf(":%s", port)

	ln, err := s.Listen("tcp", listenAddr)
	if err != nil {
		panic(err)
	}
	defer ln.Close()

	// set up reverse proxy
	url, err := url.Parse(upstreamURL)
	if err != nil {
		panic(err)
	}

	handler := httputil.NewSingleHostReverseProxy(url)
	log.Fatal(http.Serve(ln, handler))
}
