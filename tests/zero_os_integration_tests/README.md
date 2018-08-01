## Travis CI

### What does Travis build do ? 
- Setting up the testing environment in lochristi using this [script](#setup-the-testing-environment).
- Run the testsuite from travis machine.

You can trigger builds from [CI Dashboard](https://travis-dash.gig.tech)

## Run manually

### Setup the testing environment.

#### what does this script do ?
- Create zerotier network for testing.
- Setting target cpu node's ipxe_boot url.
- Reboot the target node.
- Authorize the cpu node on the zerotier network and get its zerotier ip address.

```bash 
python3 travis/zboot_env_setup.py [arguments]
```

##### Arguments

```--router_address``` : address of the router in the zerotier network.

```--router_username``` : username of the router.

```--router_password``` : password of the router.

```--zerotier_network``` : router's zerotier network.

```--zerotier_token``` : router's zerotier token.

```--rack_hostname``` : address of the racktivity device in the internal router network.

```--rack_username``` : username of the racktivity device.

```--rack_password``` : password of the racktivity device.

```--rack_module_id``` : rack module id.

```--cpu_hostname``` : cpu's hostname.

```--cpu_rack_port``` : cpu's rack port.

```--core_0_branch``` : core-0 branch.

> This script will return the zerotier network id to join, and the zero-os machine ip address.


### Run the testsuite

1- Install [0-robot](https://github.com/Jumpscale/0-robot/blob/master/docs/getting_started.md).
 
2- Change ```config.ini``` as needed.
```
cd /tests/integration_tests
vim config.ini
```

3- Install requirements.
```
cd /tests/integration_tests
pip3 install -r requirements.txt
```
   
4- Run ```prepare.sh``` to clone the framework needed for running the tests.
```
cd /tests/integration_tests
bash prepare.sh
```
   
5- Running Tests
```
cd /tests/integration_tests
nosetests -v -s testsuite --tc-file=config.ini
```
#### Note
Stesps 3, 4 and 5 can be replaced by only one step
```
cd /tests/integration_tests
bash run -d -r testsuite
```
In which
```
bash prepare.sh -h
usage:
   -h: listing  usage
   -d: install requirements
   -r: provide path for tests you want to run
```