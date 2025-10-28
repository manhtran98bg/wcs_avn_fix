sudo apt-get install redis
sudo apt install python3-venv

pushd $(dirname $0)/..
export DAL_ROOT=$PWD

if !(test -e venv);
then
(
    echo venv not exist. Create one
    python3 -m venv venv
);
else
(
    echo venv exist
);
fi

venv/bin/pip install -U pip
venv/bin/pip install -r requirements.txt

popd