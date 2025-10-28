pushd $(dirname $0)

echo "Download python, dependencies, redis"
bash download.bash

echo "Install auto start service"
bash install.bash --f

popd