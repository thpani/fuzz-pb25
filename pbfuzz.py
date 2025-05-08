#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main() -> None:
    print("Hello, World!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise
