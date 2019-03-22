#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

import pytest
import re

from unittest import mock

from qatrfm.environment import TerraformEnv


class TestTerraformEnv(object):
    """ Test TerraformEnv """

    TMP_FOLDER = '/tmp/folder'
    EXEC_RETURN = '10.1.0.'
    TFVARS = {"var1=val1", "var2=val2", "var3=val3"}
    FILENAME = 'file.tf'
    NET_OCTET = 0

    @mock.patch('qatrfm.utils.libutils.execute_bash_cmd',
                return_value=EXEC_RETURN)
    @mock.patch('shutil.copy')
    @mock.patch('tempfile.mkdtemp', return_value=TMP_FOLDER)
    def test_init_only_vars(self, mock_mkdtemp, mock_copy, mock_exec):
        mocked_TerraformEnv = TerraformEnv(self.NET_OCTET, self.TFVARS)
        assert isinstance(mocked_TerraformEnv, TerraformEnv)
        assert mocked_TerraformEnv.net_octet == self.NET_OCTET
        assert re.match(
            r'(-var \'var\d=val\d\' ){3}', mocked_TerraformEnv.tf_vars)
        assert mocked_TerraformEnv.tf_file is None
        assert mocked_TerraformEnv.snapshots is False

    def test_init_no_vars(self):
        with pytest.raises(TypeError):
            TerraformEnv()

    @mock.patch('qatrfm.utils.libutils.execute_bash_cmd',
                return_value=EXEC_RETURN)
    @mock.patch('shutil.copy')
    @mock.patch('tempfile.mkdtemp', return_value=TMP_FOLDER)
    def test_init_with_file(self, mock_mkdtemp, mock_copy, mock_exec):
        mocked_TerraformEnv_file = TerraformEnv(
            self.NET_OCTET, self.TFVARS, self.FILENAME)
        assert mocked_TerraformEnv_file.tf_file == self.FILENAME
        mock_copy.assert_called_with(
            self.FILENAME, mocked_TerraformEnv_file.workdir + '/env.tf')
