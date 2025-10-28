export FILE_SRV=${1:-"rostek_dal_wcs"}".service"

sudo systemctl stop $FILE_SRV
sudo systemctl disable $FILE_SRV
sudo rm /etc/systemd/system/$FILE_SRV