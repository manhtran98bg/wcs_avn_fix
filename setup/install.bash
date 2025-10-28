# SERVICE
pushd $(dirname $0)/..
export DAL_ROOT=$PWD
export FILE_NAME="rostek_dal_wcs.service"

while test $# -gt 0; do
  case "$1" in
    -h|--help)
        echo "Install service wcs dal"
        echo " "
        echo "bash install.bash [options | arguments]"
        echo " "
        echo "options:"
        echo "-h, --help        show brief help"
        echo "-f FILE_NAME      specify service file name"
        echo "--f, --force      specify a directory to store output in"
        exit 0
        ;;
    --f|--force)
        export FORCE=true
        shift
        ;;
    -f)
      shift
      if test $# -gt 0; then
        export FILE_NAME=$1
      else
        echo "no service file name specified"
        exit 1
      fi
      shift
      ;;
  esac
done


if !(test -e /etc/systemd/system/$FILE_NAME);
then
(
    echo Create new service
    echo "[Unit]
    Description=rostek dal for wcs
    After=network.target
    [Service]
    Type=idle
    Restart=on-failure
    RestartSec=5
    ExecStart=$DAL_ROOT/venv/bin/python main.py
    WorkingDirectory=$DAL_ROOT/scripts
    User=$USER
    [Install]
    WantedBy=multi-user.target" > $FILE_NAME

    sudo mv $FILE_NAME /etc/systemd/system
    sudo systemctl enable $FILE_NAME
    sudo systemctl start $FILE_NAME
);
elif [ $FORCE ];
then
(
    echo "Overrite service"
    sudo mv $FILE_NAME /etc/systemd/system
    sudo systemctl enable $FILE_NAME
    sudo systemctl start $FILE_NAME
);
else
(
    echo "Service existed. Try --f | --force to overrite"
);
fi

mkdir $PWD/log

popd