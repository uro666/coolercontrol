#!/bin/bash
# Taken from Fedora, modified to work with OM tooling and fix various issues.
# This script has been further modified explcitly for coolercontrol-ui with npm.
# Original version:
# https://src.fedoraproject.org/rpms/python-sphinx-book-theme/raw/rawhide/f/prepare_vendor.sh
#set -x

sudo dnf install rpmdevtools npm

PKG_URL=$(rpmdev-spectool *.spec --source 0 | sed -e 's/Source0:[ ]*//g')
PKG_TARBALL=$(realpath .)/$(basename $PKG_URL)
PKG_NAME=$(rpmspec -q --queryformat="%{NAME}" *.spec --srpm)
PKG_VERSION=$(rpmspec -q --queryformat="%{VERSION}" *.spec --srpm)
PKG_SRCDIR="${PKG_NAME}-${PKG_VERSION}/coolercontrol-ui"
PKG_DIR="$PWD"
PKG_TMPDIR=$(mktemp --tmpdir -d ${PKG_NAME}-XXXXXXXX)
PKG_PATH="$PKG_TMPDIR/$PKG_SRCDIR/"

echo "URL:     $PKG_URL"
echo "TARBALL: $PKG_TARBALL"
echo "NAME:    $PKG_NAME"
echo "VERSION: $PKG_VERSION"
echo "PATH:    $PKG_PATH"

cleanup_tmpdir() {
    popd 2>/dev/null
    rm -rf $PKG_TMPDIR
    rm -rf /tmp/npm--*
}
trap cleanup_tmpdir SIGINT

cleanup_and_exit() {
    cleanup_tmpdir
    if test "$1" = 0 -o -z "$1" ; then
        exit 0
    else
        exit $1
    fi
}

if [ ! -w "$PKG_TARBALL" ]; then
    wget "$PKG_URL"
fi

mkdir -p $PKG_TMPDIR
pushd "$PKG_TMPDIR"
tar xf $PKG_TARBALL
pwd
ls
popd

cd $PKG_PATH

export npm_config_cache="$PWD/.package-cache"
echo ">>>>>> Install npm modules"
npm ci --prefer-offline --cpu=arm64

if [ $? -ne 0 ]; then
    echo "ERROR: npm install failed"
    cleanup_and_exit 1
fi

echo ">>>>>> Package vendor files"
rm -f $PKG_DIR/${PKG_NAME}-${PKG_VERSION}-node-vendor-aarch64.tar.xz
XZ_OPT="-9e -T$(nproc)" tar cJf $PKG_DIR/${PKG_NAME}-${PKG_VERSION}-node-vendor-aarch64.tar.xz .package-cache
if [ $? -ne 0 ]; then
    cleanup_and_exit 1
fi

npm i license-report
npx license-report --only=prod --output=table --fields=name --fields=licenseType --fields=installedVersion --fields=link > $PKG_DIR/${PKG_NAME}-node-vendor-licenses.txt

cd -

rm -rf .package-cache node_modules
cleanup_and_exit 0
