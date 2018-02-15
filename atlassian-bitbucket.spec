# This file source link: https://jira.atlassian.com/browse/BSERV-10170

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

%define __os_install_post %{nil}

%define major_version 5
%define minor_version 6
%define patch_version 2
%define packagedir %{name}-%{major_version}.%{minor_version}.%{patch_version}

%define basedir %{_var}/lib/%{name}
%define appdir %{basedir}/app
%define bindir %{basedir}/bin
%define elasticdir %{basedir}/elasticsearch
%define logdir %{_var}/log/%{name}

%define userid bitbucket
%define groupid bitbucket

Name: atlassian-bitbucket
Epoch: 0
Version: %{major_version}.%{minor_version}.%{patch_version}
Release: 2%{?dist}
Summary: Atlassian Bitbucket

Group: Networking/Daemons
License: Various (see licenses directory)
URL: https://www.atlassian.com
Source0: https://www.atlassian.com/software/stash/downloads/binary/%{name}-%{version}.tar.gz
Source1: bitbucket.service
Source2: nginx-bb-ssl.conf.exaple

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

Requires: java >= 0:1.8.0
# Requires fresh git!!
Requires: git >= 0:2.14.0
Requires: git-core
Requires: git-core-doc
Requires: perl-Git
# We want to use postgresql for bitbucket database
Requires: postgresql96 postgresql96-server postgresql96-contrib postgresql96-libs
# nginx for ssl
Requires: nginx

%description
Bitbucket Server fits into the fabric of your organization to help you streamline your
development process. Integrate with Atlassian tools like Jira Software to sync pull
requests, commits, and branches without leaving Bitbucket. Plus, customize with Atlassian
Marketplace add-ons to meet your team's growing needs.

%prep
%setup -q -c -T -a 0

%build

%install
%{__rm} -rf $RPM_BUILD_ROOT
# create target directory structure
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{_sysconfdir}/logrotate.d
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{_sysconfdir}/sysconfig
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{_javadocdir}/%{name}/licenses
%{__install} -d -m 0775 ${RPM_BUILD_ROOT}%{appdir}
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{bindir}
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{elasticdir}/bin
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{elasticdir}/config-template
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{elasticdir}/lib
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{elasticdir}/modules
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{elasticdir}/plugins
%{__install} -d -m 0755 ${RPM_BUILD_ROOT}%{_var}/log/

# copy into our structure
pushd %{packagedir}
  %{__cp} -a app/* ${RPM_BUILD_ROOT}%{appdir}/
  %{__cp} -a bin/*.sh ${RPM_BUILD_ROOT}%{bindir}/
  %{__cp} -a elasticsearch/bin/{elasticsearch,elasticsearch.in.sh,plugin} ${RPM_BUILD_ROOT}%{elasticdir}/bin/
  %{__cp} -a elasticsearch/config-template/* ${RPM_BUILD_ROOT}%{elasticdir}/config-template/
  %{__cp} -a elasticsearch/lib/* ${RPM_BUILD_ROOT}%{elasticdir}/lib/
  %{__cp} -a elasticsearch/modules/* ${RPM_BUILD_ROOT}%{elasticdir}/modules/
  %{__cp} -a elasticsearch/plugins/* ${RPM_BUILD_ROOT}%{elasticdir}/plugins/
  %{__cp} -a licenses/* ${RPM_BUILD_ROOT}%{_javadocdir}/%{name}/licenses
popd
# create symlinks to the FHS locations
ln -s /home/bitbucket/log ${RPM_BUILD_ROOT}%{logdir}

# systemd service
%{__install} -m 0644  -D %{SOURCE1} \
  ${RPM_BUILD_ROOT}/usr/lib/systemd/system/bitbucket.service

# ssl conf example for nginx
%{__install} -m 0644  -D %{SOURCE2} \
  ${RPM_BUILD_ROOT}/etc/nginx/conf.d/bitbucket-ssl.conf

mkdir -p ${RPM_BUILD_ROOT}/etc/sudoers.d
echo "bitbucket ALL=(root) NOPASSWD: /sbin/zfs" > ${RPM_BUILD_ROOT}/etc/sudoers.d/bitbucket

%clean
%{__rm} -rf $RPM_BUILD_ROOT

%pre
# add the system user and group
id -g %{groupid} &>/dev/null || %{_sbindir}/groupadd -r %{groupid} 2>/dev/null
id -u %{userid} &>/dev/null || %{_sbindir}/useradd -m -c "%{summary}" -d /home/bitbucket -g %{groupid} \
  -s /bin/sh -r %{userid} 2>/dev/null

%post
systemctl daemon-reload
if [ $1 == 1 ] ; then
systemctl enable bitbucket.service

firewall-cmd --zone=public --add-port=7990/tcp --permanent
firewall-cmd --reload

/usr/pgsql-9.6/bin/postgresql96-setup initdb
sed -i '82,84s|ident|md5|' /var/lib/pgsql/9.6/data/pg_hba.conf
systemctl start postgresql-9.6
systemctl enable postgresql-9.6
sudo -u postgres /usr/bin/psql -c "CREATE ROLE bitbucketuser WITH LOGIN PASSWORD 'superpass' VALID UNTIL 'infinity';"
sudo -u postgres /usr/bin/psql -c "CREATE DATABASE bitbucket WITH ENCODING='UTF8' OWNER=bitbucketuser CONNECTION LIMIT=-1;"
fi

%preun
systemctl stop bitbucket.service
if [ "$1" = "0" ]; then
  systemctl disable bitbucket.service
fi

%files
%defattr(0644,root,root,0755)
/etc/nginx/conf.d/bitbucket-ssl.conf
/etc/sudoers.d/bitbucket
%config(noreplace) %{appdir}/WEB-INF/classes/*.properties
%config(noreplace) %{appdir}/WEB-INF/classes/*.xml
%attr(0644,root,root) %{_unitdir}/bitbucket.service
%dir %attr(0775,root,%{groupid}) %{appdir}
%{appdir}
%{elasticdir}
%attr(0775,root,%{groupid}) %{logdir}
%{_javadocdir}/%{name}/licenses
%attr(0775,root,root) %{bindir}/*.sh
%attr(0775,root,root) %{elasticdir}/bin/*

%changelog
# for 5.7:
#- elasticsearch/bin/plugin -> elasticsearch/bin/elasticsearch-plugin

* Fri Feb 2 2018 Denis Shipilov <shipilovds@gmail.com> - 5.6.2-2
- Postgresql 9.2 support will be discontinued by Atlassian soon. Postgresql 9.6 requires added.
- sudoers conf for zfs to use it by bitbucket user
- nginx conf for ssl whith bitbucket

* Thu Jan 11 2018 Denis Shipilov <shipilovds@gmail.com> - 5.6.2-1
- Updated to 5.6.2. Some cleaning & cosmetics. Add installation warnings.

* Mon Dec 18 2017 Denis Shipilov <shipilovds@gmail.com> - 5.6.1-1
- Updated to 5.6.1. Port forwarding removed.

* Wed Dec 7 2017 Denis Shipilov <shipilovds@gmail.com> - 5.5.0-1
- Updated to 5.5.0. Basedir is /var/lib/atlsassian-bitbucket now. Homedir is /home/bitbucket.

* Sat Sep 16 2017 Graham Leggett <minfrin@sharp.fm> - 5.3.1-1
- Initial packaging
