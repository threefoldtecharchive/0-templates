join_zerotier_network(){
    echo "[+] Joining zerotier network: ${1}"
    sudo zerotier-cli join ${1}; sleep 10
    memberid=$(sudo zerotier-cli info | awk '{print $3}')
    curl -s -H "Content-Type: application/json" -H "Authorization: Bearer ${2}" -X POST -d '{"config": {"authorized": true}}' https://my.zerotier.com/api/network/${1}/member/${memberid} > /dev/null
    
    while true; do
        ip=$(sudo zerotier-cli listnetworks | grep ${1} | awk '{print $8}')
        if [[ $ip == '-' ]]; then
            sleep 5
        else
            break
        fi
    done

    for interface in $(ls /sys/class/net | grep zt); do
        sudo ifconfig ${interface} mtu 1280
    done
}

echo "[+] Joining router zerotier network"
join_zerotier_network ${zerotier_network} ${zerotier_token}; sleep 10

echo "[+] Setting up testing environment ..."
python3 -u tests/integration_tests/travis/zboot_env_setup.py --router_address ${router_address} --router_username ${router_username} --router_password ${router_password} --zerotier_network ${zerotier_network} --zerotier_token ${zerotier_token} --rack_hostname ${rack_hostname} --rack_username ${rack_username} --rack_password ${rack_password} --rack_module_id ${rack_module_id} --cpu_hostname ${cpu_hostname} --cpu_rack_port ${cpu_rack_port} --core_0_branch ${core_0_branch}

echo "[+] Joining testing zerotier network"
testing_zt_network=$(cat /tmp/testing_zt_network.txt)
join_zerotier_network ${testing_zt_network} ${zerotier_token}

echo "[+] Copying testing framework ..."
cd tests/integration_tests
bash prepare.sh

echo "[+] Connecting to 0-robot server ..."
cpu_zt_ip=$(cat /tmp/cpu_zt_ip.txt)
zrobot robot connect main http://${cpu_zt_ip}:6600; sleep 20

echo "[+] Running tests ..."
nosetests -v -s ${tests_path} --tc-file=config.ini --tc=main.redisaddr:${cpu_zt_ip}