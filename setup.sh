curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo apt update
sudo apt install -y docker-ce docker-compose-plugin
sudo ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/bin/docker-compose

echo "
# NonInsidersVersion
if service docker status 2>&1 | grep -q \"is not running\"; then
    wsl.exe -d "${WSL_DISTRO_NAME}" -u root -e /usr/sbin/service docker start >/dev/null 2>&1
fi"  >> ~/.profile

