%define coolercontrolui coolercontrol-ui
%define coolercontrold coolercontrold
%define coolercontrol coolercontrol
%define appid org.coolercontrol.CoolerControl
# prevent library files from being installed
%global __cargo_is_lib() 0
# run cargotests for coolcontrold
%bcond cargotest 1

# NOTE To update:
# NOTE After updating the spec file version and saving the spec file,
# NOTE in the package dir execute package_crates to vendor and archive all
# NOTE of the cargo crates to provide Source1.
# NOTE In the package dir execute ./prepare_vendor.sh to vendor and archive
# NOTE the node modules to provide Source2.
# NOTE In the package dir execute ./prepare_vendor_aarch64.sh to vendor and archive
# NOTE the node modules to provide Source2.
# NOTE Source40 is automatically generated when running the node prepare_vendor
# NOTE script, commit the versioned file produced with the the updated spec file.

Name:		coolercontrol
Summary:	Cooling device control for Linux
Version:	4.2.1
Release:	1
License:	GPL-3.0-or-later
Group:		System/Monitoring
URL:		https://docs.coolercontrol.org
Source0:	https://gitlab.com/%{name}/%{name}/-/releases/%{version}/downloads/packages/%{name}-%{version}.tar.gz
Source1:	%{name}-%{version}-vendor.tar.xz
Source2:	%{name}-%{version}-node-vendor.tar.xz
Source3:	%{name}-%{version}-node-vendor-aarch64.tar.xz
Source40:	%{name}-node-vendor-licenses.txt

# coolercontrol
BuildRequires:	appstream-util
BuildRequires:	cmake
BuildRequires:	desktop-file-utils
BuildRequires:	hicolor-icon-theme
BuildRequires:	cmake(Qt6)
BuildRequires:	cmake(Qt6DBus)
BuildRequires:	cmake(Qt6WebEngineCore)
BuildRequires:	cmake(Qt6WebEngineWidgets)
BuildRequires:	cmake(Qt6WebChannel)
BuildRequires:	make
BuildRequires:	ninja
# coolercontrold & coolercontrolui
BuildRequires:	cargo
BuildRequires:	nodejs
BuildRequires:	npm
BuildRequires:	pkgconfig(libdrm)
BuildRequires:	pkgconfig(libdrm_amdgpu)
BuildRequires:	pkgconfig(protobuf)
BuildRequires:	rust-packaging
BuildRequires:	systemd-rpm-macros
# This is Recommends vs Requires as coolercontrol client can be used standalone
# without a local coolcontrold / daemon installed.
Recommends:	coolercontrold = %{version}-%{release}

%global _description_coolercontrol %{expand:
CoolerControl is an open-source application for monitoring and controlling
supported cooling devices.

It features an intuitive interface, flexible control options, and live
thermal data to keep your system quiet, cool, and stable.
}

%description
This is the desktop application for CoolerControl.
%_description_coolercontrol

%package	-n %{coolercontrold}
Summary:	Powerful cooling control and monitoring system daemon
Group:		System/Monitoring
# coolercontrol client is not required for coolcontrold / daemon to function
# but is recommended if coolercontrold is installed.
Recommends:	coolercontrol = %{version}-%{release}
Recommends:	lm_sensors
Recommends:	python%{pyver}dist(liquidctl)

%description -n %{coolercontrold}
This is the system daemon for CoolerControl.
%_description_coolercontrol

%prep
%autosetup -n %{name}-%{version} -p1

# set up for coolercontrolui build
pushd %{coolercontrolui}
# conditional to select arch dependent node sources
%ifarch aarch64
tar xf %{S:3}
%else
tar xf %{S:2}
%endif
popd

# set up for coolercontrold build
pushd %{coolercontrold}
# Extract vendored crates
tar xf %{S:1}
# Prep vendored crates dir
%cargo_prep -v vendor/
popd

%build
# build coolercontrolui first which is consumed by coolercontrold's build
pushd %{coolercontrolui}
# ensure these bundled web assets are not picked up instead of the built assets
rm -rf ../coolercontrold/resources/app

export npm_config_cache="$PWD/.package-cache"
npm ci --prefer-offline
npm exec vite build -- --outDir ../coolercontrold/resources/app --emptyOutDir
popd

# build coolercontrold
pushd %{coolercontrold}
export CARGO_HOME=$PWD/.cargo
%{cargo_build}
# sort out crate licenses
%cargo_license_summary
%{cargo_license} > LICENSES.dependencies
popd

# build coolercontrol
pushd %{coolercontrol}
%cmake -G Ninja
%ninja_build
popd

%install
# coolercontrold
pushd %{coolercontrold}/daemon
%{cargo_install}
#--root=%{buildroot}%{_prefix}
rm -rf %{buildroot}%{_datadir}/cargo
popd

pushd %{coolercontrold}
install -Dpm 0644 systemd/%{coolercontrold}.service -t %{buildroot}%{_unitdir}
install -Dpm 0644 man/%{coolercontrold}.8 -t %{buildroot}%{_mandir}/man8
install -Dpm 0644 LICENSES.dependencies -t %{buildroot}%{_datadir}/licenses/%{coolercontrold}
popd
install -Dpm 0644 %{S:40} -t %{buildroot}%{_datadir}/licenses/%{coolercontrold}

# coolercontrol
pushd %{coolercontrol}
%ninja_install -C build

desktop-file-install --dir=%{buildroot}%{_datadir}/applications metadata/%{appid}.desktop
install -Dpm 0644 metadata/%{appid}.svg -t %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -Dpm 0644 metadata/%{appid}-alert.svg -t %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -Dpm 0644 metadata/%{appid}-symbolic.svg -t %{buildroot}%{_datadir}/icons/hicolor/symbolic/apps
install -Dpm 0644 metadata/%{appid}-symbolic-alert.svg -t %{buildroot}%{_datadir}/icons/hicolor/symbolic/apps
install -Dpm 0644 metadata/%{appid}.png -t %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
install -Dpm 0644 metadata/%{appid}-alert.png -t %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
install -Dpm 0644 metadata/%{appid}.metainfo.xml -t %{buildroot}%{_metainfodir}
install -Dpm 0644 man/%{name}.1 -t %{buildroot}%{_mandir}/man1

# Install the additional sizes of desktop icons for 32^2, 64^2, 128^2
for size in 32x32 64x64 128x128; do
    install -Dpm 0644 icons/$size.png \
        %{buildroot}%{_datadir}/icons/hicolor/$size/apps/%{appid}.png
done
popd

%check
# coolercontrol
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml
%{buildroot}%{_bindir}/%{coolercontrold} --version

%if %{with cargotest}
# coolercontrold tests
pushd %{coolercontrold}
%{cargo_test} --frozen
popd
%endif

%post -n %{coolercontrold}
%systemd_post %{coolercontrold}.service

%preun -n %{coolercontrold}
%systemd_preun %{coolercontrold}.service

%postun -n %{coolercontrold}
%systemd_postun_with_restart %{coolercontrold}.service

%files
%doc README.md CHANGELOG.md
%license LICENSE
%{_bindir}/%{name}
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}-alert.svg
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_datadir}/icons/hicolor/symbolic/apps/%{appid}-symbolic-alert.svg
%{_datadir}/icons/hicolor/symbolic/apps/%{appid}-symbolic.svg
%{_datadir}/icons/hicolor/256x256/apps/%{appid}-alert.png
%{_datadir}/icons/hicolor/*x*/apps/%{appid}.png
%{_metainfodir}/%{appid}.metainfo.xml
%{_mandir}/man1/%{name}.1.*

%files -n %{coolercontrold}
%doc README.md CHANGELOG.md
%license LICENSE %{coolcontrold}/LICENSES.dependencies %{name}-node-vendor-licenses.txt
%{_bindir}/%{coolercontrold}
%{_unitdir}/%{coolercontrold}.service
%{_mandir}/man8/%{coolercontrold}.8.*
