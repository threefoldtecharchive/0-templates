echo "clone 0-template repo from ${1} branch"
git clone https://github.com/threefoldtech/0-templates -b ${1}
cd 0-templates
./utils/zrobot_install.sh
cd tests
pip3 install -r requirements.txt
sudo ln -sf /usr/sbin/zerotier-cli /opt/bin/zerotier-cli
sed -i -e"s/^remote_server=.*/remote_server=http:\/\/${2}:6600/" config.ini
sed -i -e"s/^zt_client=.*/zt_client=${3}/" config.ini
sed -i -e"s/^zt_netwrok_id=.*/zt_netwrok_id=${4}/" config.ini
