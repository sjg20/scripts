#!/bin/sh

less $(ls -tr /build/*/tmp/portage/logs/*.log | tail -1)

