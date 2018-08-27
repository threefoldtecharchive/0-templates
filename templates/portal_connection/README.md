## template: github.com/threefoldtech/0-templates/portal_connection/0.0.1

### Description:

This template is responsible for to register a node robot to a portal robot.

It works by sending an HTTP POST request to the portal in order to register the robot in the portal

### Schema:
- url: URL of the portal API endpoint used to register the robot

### Actions:
- install: send a POST request to the url specified in the schema with the required information for the portal to track a robot.
- uninstall: will send a DELETE request to the portal to stop tracking this robot in the portal