## template: github.com/0-templates/zrobot_config/0.0.1

### Description:

This template is responsible for configuring a 0-robot to use 0-db as storage for it's service data.
Once this service is installed, it write a specific file on the 0-OS then restarts the robot.
The robot will then restart automatically and check for the existence of the file, if it finds it, it will use the url contained in the file
to reach the 0-db and use it for storage

### Schema:

- `dataRepo`: url pointing to the 0-db to use to store the robot data.
    format of the url is `zdb://admin_passwd@hostname:port/namespace`. The only required field being the hostname, all the other are optional.
    Here is a list of all possiblities:
    - `zdb://hostname`
    - `zdb://hostname:port`
    - `zdb://admin_passwd@hostname:port`
    - `zdb://admin_passwd@hostname:port`
    - `zdb://admin_passwd@hostname:port/namespace`

### Actions:

- `install`: writes the configuration file and restart the robot
- `delete`: deletes the configuration file and restart the robot
