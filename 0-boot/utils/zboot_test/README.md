# Zboot environment test script

This script is meant to quickly test a zeroboot environment.

Variables for the test are set as static arguments at the top of the script.

What this test will do is make reservations of free hosts in the provided pool service (`ZEROBOOT_POOL`) on the provided robot instance (`ROBOT_INSTANCE` that should already be connected with on the host).

It will make the reservations in groups defined by `MAX_RESERVATIONS_PER_RUN` or until there are no more free hosts left to reserve if less.

Each reservation should boot with zero-os and the script will Ping the reserved hosts using the zos-client, so the `BOOT_URL` should contain the `development` boot parameter.

Then for each reservation, the robot that's running on it will be called and asked to run a a single VM service running ubuntu and 1 disk.
When the VM comes online, the script will SSH into it and print the OS information running on the VM (which should be ubuntu 16.04 or the OS provided in the `flist` parameter in `VM_DATA` if changed)

Run the script with:
```py
python3 test_zboot.py
```
