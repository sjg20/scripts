#!/usr/bin/python3
# Insert a header #include into all files that have a particular function call
# in them

from optparse import OptionParser
import os
import re
import string
import sys
import unittest

sys.path.append('/home/sjg/u/tools/patman')

import command

UBOOT = '__UBOOT__'
ALPHANUM = set(string.ascii_lowercase + string.ascii_uppercase + string.digits +
               '_')

def not_supported(msg, line):
    print('%s: %s' % (msg, line))


def process_data(data, func, insert_hdr, ignore_fragments):
    """Process a C file by adding a header to it if needed

    Args:
        data: String containing the file contents
        func: Symbol that is provided by the header (e.g. 'BUG(')
        insert_hdr: Header to add (e.g. 'command.h', 'linux/bug.h')
        ignore_fragments: True to check that the file actually has the
            identifier. This will ignore 'PRBUG(' when looking for 'BUG(', for
            example

    Returns:
        One of:
           List of all lines in the file (each a string) if the header was added
           None if the header was not added
           str if the header was not added and there is a message
    """
    if func and func not in data:
        return None
    to_add = '#include <%s>' % insert_hdr
    if to_add in data:
        return None
    lines = data.splitlines()

    # Make sure that at least one match is the full match string. For example
    # this will ignore PRBUG() when looking for BUG(
    if ignore_fragments:
        found = False
        for line in lines:
            start = 0
            while True:
                pos = line.find(func, start)
                if pos == -1:
                    break
                if pos == 0 or line[pos - 1] not in ALPHANUM:
                    found = True
                    break
                start = pos + 1
            if found:
                break
        if not found:
            return None

    out = []
    done = False
    found_includes = False
    active = True  # We are not in an #ifndef
    for line in lines:
        #if line.strip() and not done:
        if not done:
            if line.startswith('#if'):
                tokens = line.split(' ')
                if len(tokens) == 2:
                    cond, sym = tokens
                    if sym == UBOOT:
                        if cond == '#ifdef':
                            active = True
                        elif cond == '#ifndef':
                            active = False
                        else:
                            not_supported('unknown condition', line)
            elif line.startswith('#else'):
                if active:
                    out.append(to_add)
                    done = True
                active = not active
            elif line.startswith('#endif'):
                # We got to an #endif and didn't add the header yet
                if active:
                    out.append(to_add)
                    done = True
                active= True
            elif active:
                if line.startswith('#include'):
                    m = re.match('#include <(.*)>', line)
                    if m:
                        hdr = m.group(1)
                        if hdr != 'common.h':
                            has_subdir = '/' in hdr
                            insert_has_subdir = '/' in insert_hdr
                            todo = False
                            if has_subdir == insert_has_subdir:
                                todo = insert_hdr < hdr
                            elif has_subdir:
                                todo = True
                            if todo:
                                out.append(to_add)
                                done = True
                    else:
                        # If the first include is a local file then probably
                        # the inclusion is handled by that file.
                        if found_includes:
                            # Put it before the first local #include "..."
                            out.append(to_add)
                        else:
                            inc_name = line.split(' ')[1]
                            return ("local include %s" % inc_name)
                        done = True
                    found_includes = True
                elif found_includes:
                    out.append(to_add)
                    done = True
        out.append(line)
    return out

def process_file(fname, func, insert_hdr, skipped, ignore_fragments):
    skip = False
    suffix = fname[-2:]
    if suffix == '.h':
        if fname.startswith('include/linux'):
            return
        skip = True
    elif suffix != '.c':
        return
    with open(fname, 'r') as fd:
        data = fd.read()
    out = process_data(data, func, insert_hdr, ignore_fragments)
    if out:
        if skip:
            # Don't process this but indicate that it needs a look
            if fname in skipped:
                skiped[fname].append(func)
            else:
                skipped[fname] = [func]
        elif isinstance(out, str):
            print('Check %s: %s' % (fname, out))
        else:
            with open(fname, 'w') as fd:
                for line in out:
                    print(line, file=fd)


def doit(func, insert_hdr, skipped, ignore_fragments):
    fnames = command.Output('git', 'grep', '-l', func).splitlines()
    for fname in fnames:
        if os.path.islink(fname):
            continue
        if fname.startswith('tools/') or fname.startswith('scripts/'):
            continue
        if fname.startswith('tools/') or fname.startswith('scripts/'):
            continue
        process_file(fname, func, insert_hdr, skipped, ignore_fragments)

def process_files_from(list_fname, insert_hdr):
    with open(list_fname) as fd:
        for fname in fd.readlines():
            fname = fname.strip()
            print(fname, insert_hdr)
            process_file(fname, None, insert_hdr)


class HdrConv:
    def __init__(self):
        self.hdr = None
        self.searches = []

    def set_hdr(self, hdr):
        self.hdr = hdr

    def add_funcs(self, funcs, ignore_fragments=True):
        self.searches.append(['(', funcs, ignore_fragments])

    def add_text(self, funcs, ignore_fragments=True):
        self.searches.append(['', funcs, ignore_fragments])

    def run(self):
        skipped = {}
        for prefix, funcs, ignore_fragments in self.searches:
            for item in funcs.split(','):
                doit(item + prefix, self.hdr, skipped, ignore_fragments)
        for fname in sorted(skipped.keys()):
            print("Skipping file '%s': %s" % (fname, skipped[fname]))


class TestEntry(unittest.TestCase):
    def testSimple(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#include <common.h>
#include <abs.h>
#include <stdio.h>
'''
        out = process_data(hdrs + body, 'abs(', 'abs.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testNoMatch(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
'''
        body = '''
int some_func(void)
{
    another(123);
}
'''
        expect = hdrs
        out = process_data(hdrs + body, 'abs(', 'abs.h', False)
        self.assertIsNone(out)

    def testLinuxEnd(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#include <common.h>
#include <stdio.h>
#include <linux/bug.h>
'''
        out = process_data(hdrs + body, 'abs(', 'linux/bug.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testAsm(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
#include <linux/types.h>
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#include <linux/types.h>
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testIfndef(self):
        hdrs= '''
#ifndef __UBOOT__
#include <sys/types.h>
#else
#include <common.h>
#include <stdio.h>
#include <linux/types.h>
#endif
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#ifndef __UBOOT__
#include <sys/types.h>
#else
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#include <linux/types.h>
#endif
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testIfdef(self):
        hdrs= '''
#ifdef __UBOOT__
#include <common.h>
#include <stdio.h>
#include <linux/types.h>
#else
#include <sys/types.h>
#endif
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#ifdef __UBOOT__
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#include <linux/types.h>
#else
#include <sys/types.h>
#endif
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)


#ifndef __UBOOT__
#include <log.h>
#include <dm/devres.h>
#include <linux/crc32.h>
#include <linux/err.h>
#include <u-boot/crc.h>
#else
#include <div64.h>
#include <malloc.h>
#include <ubi_uboot.h>
#endif
#include <linux/bug.h>

    def testEndif(self):
        hdrs= '''
#ifndef __UBOOT__
#include <sys/types.h>
#else
#include <common.h>
#include <stdio.h>
#endif
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#ifndef __UBOOT__
#include <sys/types.h>
#else
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#endif
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testElse(self):
        hdrs= '''
#ifdef __UBOOT__
#include <common.h>
#include <stdio.h>
#else
#include <sys/types.h>
#endif
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#ifdef __UBOOT__
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#else
#include <sys/types.h>
#endif
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testLocal(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
#include "something.h"
'''
        body = '''
int some_func(void)
{
    abs(123);
}
'''
        expect = '''
#include <common.h>
#include <stdio.h>
#include <asm/io.h>
#include "something.h"
'''
        out = process_data(hdrs + body, 'abs(', 'asm/io.h', False)
        new_hdrs = out[:-len(body.splitlines())]
        self.assertEqual(expect.splitlines(), new_hdrs)

    def testPartial(self):
        hdrs= '''
#include <common.h>
#include <stdio.h>
'''
        body = '''
int some_func(void)
{
    PDEBUG(123);
}
'''
        out = process_data(hdrs + body, 'BUG(', 'linux/bug.h', True)
        self.assertIsNone(out)

    def testNoStdIncludes(self):
        """Don't add anything if the first include is a local file"""
        hdrs= '''
#include "local.h"
'''
        body = '''
int some_func(void)
{
    BUG(123);
}
'''
        out = process_data(hdrs + body, 'BUG(', 'linux/bug.h', True)
        self.assertEqual("local include \"local.h\"", out)


#all = 'ENV_VALID,ENV_INVALID,ENV_REDUND'.split(',')
#all = 'env_op_create,env_op_delete,env_op_overwrite'.split(',')
#for item in all:
	#doit(item, 'search.h')

#all = 'U_BOOT_ENV_CALLBACK'.split(',')
#for item in all:
	#doit(item, 'env_callback.h')

#all = 'ENV_INVALID,ENV_INVALID,ENV_REDUND'.split(',')
#for item in all:
	#doit(item, 'env.h')

#all = 'CONFIG_ENV_SIZE,CONFIG_ENV_SECT_SIZE,ENV_OFFSET,CONFIG_ENV_ADDR'.split(',')
#all += 'ENV_IS_EMBEDDED,CONFIG_SYS_REDUNDAND_ENVIRONMENT,CONFIG_ENV_OFFSET'.split(',')
#all += 'CONFIG_SYS_REDUNDAND_ENVIRONMENT,ENV_HEADER_SIZE'.split(',')
#for item in all:
	#doit(item, 'environment.h')

#all = 'H_NOCLEAR,H_FORCE,H_INTERACTIVE,H_HIDE_DOT,H_MATCH_KEY,H_MATCH_DATA'
#all += ',H_MATCH_BOTH,H_MATCH_IDENT,H_MATCH_SUBSTR,H_MATCH_REGEX,H_MATCH_METHOD'
#all += ',H_PROGRAMMATIC,H_ORIGIN_FLAGS'
#for item in all.split(','):
	#doit(item, 'environment.h')

#all = 'ENVL_,ENV_CALLBACK_LIST_STATIC'
#for item in all.split(','):
	#doit(item, 'environment.h')


#all = 'crc32,crc32_wd,crc32_no_comp'
#for item in all.split(','):
	#doit(item + '(', 'u-boot/crc.h.h')

#all = 'qsort,strcmp_compar'
#for item in all.split(','):
	#doit(item + '(', 'sort.h')

#all = 'strmhz'
#for item in all.split(','):
	#doit(item + '(', 'vsprintf.h')

#all = 'serial_printf'
#for item in all.split(','):
	#doit(item + '(', 'serial.h')

#all = 'serial_init,serial_setbrg,serial_putc,serial_putc_raw,serial_puts'
#all += ',serial_getc,serial_tstc'
#for item in all.split(','):
	#doit(item + '(', 'serial.h')

#all = 'usec2ticks,ticks2usec'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'wait_ticks'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'timer_get_us,get_ticks'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'mii_init'
#for item in all.split(','):
	#doit(item + '(', 'linux/mii.h')

#all = 'checkcpu'
#for item in all.split(','):
	#doit(item + '(', 'cpu.h')

#all = 'smp_set_core_boot_addr,smp_kick_all_cpus'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'icache_status,icache_enable,icache_disable,dcache_status,dcache_enable,'
#all += 'dcache_disable,mmu_disable'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'cpu_numcores,cpu_num_dspcores,cpu_mask,cpu_dsp_mask,is_core_valid,'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'enable_caches,flush_cache,flush_dcache_all,flush_dcache_range'
#all += ',invalidate_dcache_range,invalidate_dcache_all,invalidate_icache_all'
#all += ',cleanup_before_linux_select'
#for item in all.split(','):
	#doit(item + '(', 'cpu_legacy.h')

#all = 'interrupt_init,timer_interrupt,external_interrupt,irq_install_handler'
#all += ',irq_free_handler,reset_timer'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

#all = 'enable_interrupts,disable_interrupts'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

#all = 'run_command,run_command_repeatable,run_command_list'
#for item in all.split(','):
	#doit(item + '(', 'command.h')

#all = 'interrupt_handler_t'
#for item in all.split(','):
	#doit(item, 'irq_legacy.h')

#all = 'board_get_usable_ram_top'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'board_fix_fdt,board_late_init,board_postclk_init,board_early_init_r'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'pci_init_board'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'trap_init'
#for item in all.split(','):
	#doit(item + '(', 'irq_legacy.h')

#all = 'eeprom_init,eeprom_read,eeprom_write'
#for item in all.split(','):
	#doit(item + '(', 'eeprom_legacy.h')

#all = 'coloured_LED_init,red_led_on,red_led_off,green_led_on,green_led_off,'
#all += 'yellow_led_on,yellow_led_off,blue_led_on,blue_led_off'
#for item in all.split(','):
	#doit(item + '(', 'status_led.h')

#all = 'flash_perror'
#for item in all.split(','):
	#doit(item + '(', 'flash.h')

#all = 'do_fat_fsload,do_ext2load'
#for item in all.split(','):
	#doit(item + '(', 'fs.h')

#all = 'relocate_code'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'jumptable_init'
#for item in all.split(','):
	#doit(item + '(', 'exports.h')

#all = 'reset_phy'
#for item in all.split(','):
	#doit(item + '(', 'net.h')

#all = 'arch_fixup_fdt'
#for item in all.split(','):
	#doit(item + '(', 'fdt_support.h')

#all = 'll_boot_init'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'get_clocks,get_bus_freq,get_serial_clock'
#for item in all.split(','):
	#doit(item + '(', 'clock_legacy.h')

#all = 'get_tbclk'
#for item in all.split(','):
	#doit(item + '(', 'time.h')

#all = 'image_load_addr,image_save_addr,image_save_size'
#for item in all.split(','):
	#doit(item, 'image.h')

#all = 'get_ram_size,get_effective_memsize'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'testdram'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'hang'
#for item in all.split(','):
	#doit(item + '(', 'hang.h')

#all = 'uuid_str_valid,uuid_str_to_bin,uuid_bin_to_str,uuid_guid_get_bin,'
#all += 'uuid_guid_get_str,gen_rand_uuid,gen_rand_uuid_str'
#for item in all.split(','):
	#doit(item + '(', 'uuid.h')

#all = 'flash_init,flash_print_info,flash_erase,flash_sect_erase,'
#all += 'flash_sect_protect,flash_sect_roundb,long flash_sector_size,'
#all += 'flash_set_verbose,flash_protect,flash_write,addr2info,write_buff,'
#all += 'cfi_mtd_init,flash_real_protect,flash_read_user_serial,'
#all += 'flash_read_factory_serial,board_flash_get_legacy,jedec_flash_match'
#for item in all.split(','):
	#doit(item + '(', 'flash.h')

#all = 'flash_info_t'
#for item in all.split(','):
	#doit(item, 'flash.h')

#all = 'add_ip_checksums,arp_is_waiting,compute_ip_checksum,copy_filename,do_tftpb,env_get_ip,env_get_vlan,eth_env_get_enetaddr_by_index,eth_env_set_enetaddr_by_index,eth_get_dev,eth_get_dev,eth_get_dev_by_index,eth_get_dev_by_name,eth_get_dev_by_name,eth_get_dev_index,eth_get_ethaddr,eth_get_ethaddr,eth_get_name,eth_halt,eth_halt_state_only,eth_halt_state_only,eth_init,eth_init_state_only,eth_init_state_only,eth_initialize,eth_is_active,eth_is_active,eth_is_on_demand_init,eth_mcast_join,eth_parse_enetaddr,eth_receive,eth_register,eth_rx,eth_send,eth_set_current,eth_set_last_protocol,eth_try_another,eth_unregister,eth_write_hwaddr,ip_checksum_ok,ip_to_string,is_broadcast_ethaddr,is_cdp_packet,is_multicast_ethaddr,is_serverip_in_cmd,is_valid_ethaddr,is_zero_ethaddr,nc_input_packet,nc_start,net_auto_load,net_copy_ip,net_copy_u32,net_eth_hdr_size,net_get_arp_handler,net_get_async_tx_pkt_buf,net_get_udp_handler,net_init,net_loop,net_parse_bootfile,net_process_received_packet,net_random_ethaddr,net_read_ip,net_read_u32,net_send_ip_packet,net_send_packet,net_send_udp_packet,net_set_arp_handler,net_set_ether,net_set_icmp_handler,net_set_ip_header,net_set_state,net_set_timeout_handler,net_set_udp_handler,net_set_udp_header,net_start_again,net_update_ether,net_write_ip,random_port,reset_phy,string_to_ip,string_to_vlan,update_tftp,usb_eth_initialize,usb_ether_init,vlan_to_string'
#for item in all.split(','):
	#doit(item + '(', 'net.h')

#all = 'ARP_HLEN'
#for item in all.split(','):
	#doit(item, 'net.h')

#all = 'blk_get_dev,blk_get_dev,blk_get_device_by_str,blk_get_device_by_str,blk_get_device_part_str,blk_get_device_part_str,dev_print,dev_print,get_disk_guid,gpt_fill_header,gpt_fill_pte,gpt_restore,gpt_verify_headers,gpt_verify_partitions,host_get_dev_err,is_valid_dos_buf,is_valid_gpt_buf,mg_disk_get_dev,mg_disk_get_dev,part_get_info,part_get_info,part_get_info_by_dev_and_name_or_num,part_get_info_by_name,part_get_info_by_name_type,part_get_info_whole_disk,part_get_info_whole_disk,part_init,part_init,part_print,part_print,part_set_generic_name,write_gpt_table,write_mbr_and_gpt_partitions,write_mbr_partition'
#for item in all.split(','):
	#doit(item + '(', 'part.h')

#all = 'lbaint_t'
#for item in all.split(','):
	#doit(item, 'blk.h')

#all = 'AMIGA_ENTRY_NUMBERS,BOOT_PART_COMP,BOOT_PART_TYPE,DEV_TYPE_CDROM,DEV_TYPE_HARDDISK,DEV_TYPE_OPDISK,DEV_TYPE_TAPE,DEV_TYPE_UNKNOWN,DOS_ENTRY_NUMBERS,ISO_ENTRY_NUMBERS,LOG2,LOG2_INVALID,MAC_ENTRY_NUMBERS,MAX_SEARCH_PARTITIONS,PART_NAME_LEN,PART_TYPE_AMIGA,PART_TYPE_DOS,PART_TYPE_EFI,PART_TYPE_ISO,PART_TYPE_LEN,PART_TYPE_MAC,PART_TYPE_UNKNOWN,U_BOOT_PART_TYPE,_PART_H,part_get_info_ptr,part_get_info_ptr,part_get_info_ptr,part_print_ptr,part_print_ptr'
#for item in all.split(','):
	#doit(item, 'part.h')

#all = 'blk_common_cmd'
#for item in all.split(','):
	#doit(item + '(', 'blk.h')

#all = 'struct blk'
#for item in all.split(','):
	#doit(item, 'blk.h')

#all= 'bootstage_accum,bootstage_accum,bootstage_add_record,bootstage_add_record,bootstage_error,bootstage_error,bootstage_fdt_add_report,bootstage_get_size,bootstage_get_size,bootstage_init,bootstage_init,bootstage_mark,bootstage_mark,bootstage_mark_code,bootstage_mark_code,bootstage_mark_name,bootstage_mark_name,bootstage_relocate,bootstage_relocate,bootstage_report,bootstage_start,bootstage_start,bootstage_stash,bootstage_stash,bootstage_unstash,bootstage_unstash,show_boot_progress,timer_get_boot_us'
#for item in all.split(','):
	#doit(item + '(', 'bootstage.h')

#all = 'BOOTSTAGE_ID'
#for item in all.split(','):
	#doit(item, 'bootstage.h')

#all = 'android_image_check_header,android_image_get_end,android_image_get_kcomp,android_image_get_kernel,android_image_get_kload,android_image_get_ramdisk,android_image_get_second,android_print_contents,board_fit_config_name_match,board_fit_image_post_process,boot_fdt_add_mem_rsv_regions,boot_get_cmdline,boot_get_fdt,boot_get_fdt_fit,boot_get_fpga,boot_get_kbd,boot_get_loadable,boot_get_ramdisk,boot_get_setup,boot_get_setup_fit,boot_ramdisk_high,boot_relocate_fdt,booti_setup,bootz_setup,calculate_hash,env_get_bootm_low,env_get_bootm_mapsize,env_get_bootm_size,fdt_getprop_u32,fit_add_verification_data,fit_all_image_verify,fit_check_format,fit_check_ramdisk,fit_conf_find_compat,fit_conf_get_node,fit_conf_get_prop_node,fit_conf_get_prop_node_count,fit_conf_get_prop_node_index,fit_config_verify,fit_find_config_node,fit_get_desc,fit_get_end,fit_get_name,fit_get_node_from_config,fit_get_size,fit_get_subimage_count,fit_get_timestamp,fit_image_check_arch,fit_image_check_comp,fit_image_check_os,fit_image_check_sig,fit_image_check_target_arch,fit_image_check_type,fit_image_get_arch,fit_image_get_comp,fit_image_get_data,fit_image_get_data_and_size,fit_image_get_data_offset,fit_image_get_data_position,fit_image_get_data_size,fit_image_get_entry,fit_image_get_load,fit_image_get_node,fit_image_get_os,fit_image_get_type,fit_image_hash_get_algo,fit_image_hash_get_value,fit_image_load,fit_image_print,fit_image_verify,fit_image_verify_required_sigs,fit_image_verify_with_data,fit_parse_conf,fit_parse_subimage,fit_print_contents,fit_region_make_list,fit_set_timestamp,genimg_get_arch_id,genimg_get_arch_name,genimg_get_arch_short_name,genimg_get_cat_count,genimg_get_cat_desc,genimg_get_cat_name,genimg_get_cat_short_name,genimg_get_comp_id,genimg_get_comp_name,genimg_get_comp_short_name,genimg_get_format,genimg_get_kernel_addr,genimg_get_kernel_addr_fit,genimg_get_os_id,genimg_get_os_name,genimg_get_os_short_name,genimg_get_type_id,genimg_get_type_name,genimg_get_type_short_name,genimg_has_config,genimg_print_size,genimg_print_time,get_table_entry_id,get_table_entry_name,image_check_arch,image_check_dcrc,image_check_hcrc,image_check_magic,image_check_os,image_check_target_arch,image_check_type,image_decomp,image_get_checksum_algo,image_get_crypto_algo,image_get_data,image_get_data_size,image_get_header_size,image_get_host_blob,image_get_image_end,image_get_image_size,image_get_name,image_get_padding_algo,image_multi_count,image_multi_getimg,image_print_contents,image_set_host_blob,image_set_name,image_setup_libfdt,image_setup_linux,image_source_script,memmove_wd'
#for item in all.split(','):
	#doit(item + '(', 'image.h')

#all = 'image_get_magic'
#for item in all.split(','):
	#doit(item + '(', 'image.h')

#all = 'IH_ARCH_,IH_OS_,IH_MAGIC,bootm_headers_t,struct image_header'
#for item in all.split(','):
	#doit(item, 'image.h')

#all = 'struct lmb'
#for item in all.split(','):
	#doit(item, 'lmb.h')

#all = 'fdt_status_,fdt_find_,fdt_fixup_'
#for item in all.split(','):
	#doit(item, 'fdt_support.h')

#all = 'fdt_for_each_subnode,fdt_node_offset_by_compat_reg,fdt_set_phandle'
#all += ',fdt_alloc_phandle'
#for item in all.split(','):
	#doit(item + '(', 'linux/libfdt.h')

#all = 'fdt_for_'
#for item in all.split(','):
	#doit(item, 'linux/libfdt.h')

#all = 'hash_block'
#for item in all.split(','):
	#doit(item + '(', 'hash.h')


#all = 'fdt_node_'
#for item in all.split(','):
	#doit(item, 'linux/libfdt.h')

#all = 'arch_cpu_init,arch_cpu_init_dm,arch_early_init_r,arch_fsp_init,arch_reserve_stacks,arch_setup_gd,board_early_init_f,board_early_init_r,board_fix_fdt,board_get_usable_ram_top,board_init_f,board_init_f_alloc_reserve,board_init_f_init_reserve,board_init_r,board_late_init,board_postclk_init,checkboard,cpu_init_r,dram_init,dram_init_banksize,embedded_dtb_select,get_effective_memsize,get_ram_size,init_cache_f_r,init_func_vid,last_stage_init,mac_read_from_eeprom,mach_cpu_init,main_loop,misc_init_f,misc_init_r,pci_init,pci_init_board,print_cpuinfo,relocate_code,relocate_code,reserve_mmu,set_cpu_clk_info,show_board_info,testdram,timer_init,trap_init,update_flash_size'
#for item in all.split(','):
	#doit(item + '(', 'init.h')

#all = 'monitor_flash_len'
#for item in all.split(','):
	#doit(item, 'init.h')

#all = 'log,debug,assert,warn_non_spl,assert_noisy,log_ret,log_msg_ret,log_init'
#all += ',log_err,log_warning,log_notice,log_info,log_debug,log_content,log_io'
#all += ',debug_cond'
#for item in all.split(','):
	#print(item)
	#doit(item + '(', 'log.h')

#all = 'CMD_RET_,U_BOOT_CMD'
#for item in all.split(','):
	#doit(item, 'command.h')
#all = 'fixup_cmdtable,cmd_auto_complete'
#all += ',_do_help,board_run_command,bootm_maybe_autostart,bootm_maybe_autostart,cmd_always_repeatable,cmd_auto_complete,cmd_discard_repeatable,cmd_get_data_size,cmd_is_repeatable,cmd_never_repeatable,cmd_process,cmd_process_error,cmd_usage,common_diskboot,complete_subcmdv,do_bootd,do_booti,do_bootm,do_bootz,do_env_print_efi,do_env_set_efi,do_go_exec,do_poweroff,do_reset,do_run,find_cmd,find_cmd_tbl,fixup_cmdtable,run_command,run_command_list,run_command_repeatable,var_complete'
#for item in all.split(','):
	#doit(item + '(', 'command.h')

#all = 'env_set,env_relocate,env_get,env_set_addr'
#for item in all.split(','):
	#doit(item + '(', 'env.h')

#all = 'EFI_ENTRY'
#for item in all.split(','):
	#doit(item, 'efi_loader.h')

#ctags -x --c-types=fp include/log.h |cut -d' ' -f1 >asc
#ctags -x --c-types=d include/log.h |cut -d' ' -f1 >>asc
#(for f in `cat asc`; do cscope -d  -L3 $f; done) |cut -d' ' -f1 |sort |uniq

#process_files_from('files', 'log.h')

#all = 'show_regs,valid_user_regs,instruction_pointer,pc_pointer,processor_mode,'
#all += 'interrupts_enabled'

#for item in all.split(','):
	#doit(item + '(', 'asm/ptrace.h')

def asm_offsets(hdr):
    hdr.set_hdr('asm-offsets.h')
    all = 'GENERATED_GBL_DATA_SIZE,GENERATED_BD_INFO_SIZE,GD_SIZE,GD_BD'
    all += ',GD_MALLOC_BASE,GD_RELOCADDR,GD_RELOC_OFF,GD_START_ADDR_SP,GD_NEW_GD'
    all += ',CONFIG_SYS_GBL_DATA_OFFSET'
    hdr.add_text(all)

def bug(hdr):
    hdr.set_hdr('linux/bug.h')
    hdr.add_funcs('BUG,BUG_ON,WARN,WARN_ON,WARN_ON_ONCE,WARN_ONCE')
    hdr.add_text('BUILD_BUG_', ignore_fragments=False)

#all = '__stringify'
#for item in all.split(','):
	#doit(item + '(', 'linux/stringify.h')

#all = 'udelay,__udelay,mdelay,ndelay'
#for item in all.split(','):
	#doit(item + '(', 'linux/delay.h')

#all = 'BIT,BITS_TO_LONGS,BIT_MASK,BIT_ULL,BIT_ULL_MASK,BIT_ULL_WORD,BIT_WORD,GENMASK,GENMASK,GENMASK_ULL,__clear_bit,__set_bit,ffs,fls'
#for item in all.split(','):
	#doit(item + '(', 'linux/bitops.h')

#all = 'ft_cpu_setup,ft_pci_setup,arch_fixup_fdt'
#for item in all.split(','):
	#doit(item + '(', 'fdt_support.h')

#all = 'va_start'
#for item in all.split(','):
	#doit(item + '(', 'stdarg.h')

#all = 'display_options,display_options_get_banner,display_options_get_banner_priv,print_buffer,print_freq,print_size'
#for item in all.split(','):
	#doit(item + '(', 'display_options.h')

##all = 'fgetc,fputc,fputs,ftstc,getc,putc,puts,tstc,vprintf'
#for item in all.split(','):
	#doit(item + '(', 'stdio.h')

#all = 'GD_FLG,gd->,gd_board_type'
#for item in all.split(','):
	#doit(item, 'asm/global_data.h')

#all = 'bd->,\\->bi_'
#for item in all.split(','):
	#doit(item, 'asm/u-boot.h')

#all = 'KERN_ALERT,KERN_CONT,KERN_CRIT,KERN_DEBUG,KERN_EMERG,KERN_ERR,KERN_INFO,KERN_NOTICE,KERN_WARNING,__KERNEL_PRINTK__,__printk,no_printk,pr_alert,pr_cont,pr_crit,pr_debug,pr_debug,pr_devel,pr_devel,pr_emerg,pr_err,pr_fmt,pr_info,pr_notice,pr_warn,pr_warning,printk,printk_once'
#for item in all.split(','):
	#doit(item, 'linux/printk.h')

#all = 'ARCH_DMA_MINALIGN,MMU_SECTION_SIZE,MMU_SECTION_SHIFT,DCACHE_,PGTABLE_SIZE'
#for item in all.split(','):
	#doit(item, 'asm/cache.h')

#all = 'arm_init_before_mmu,arm_init_domains,check_cache_range,cpu_cache_initialization,dram_bank_mmu_setup,invalidate_l2_cache,l2_cache_disable,l2_cache_enable,set_section_dcache'
#all += ',current_el,read_mpidr,__asm_flush_dcache_range,psci_system_reset,smc_call'
#all += ',__asm_flush_dcache_all,__asm_flush_dcache_range,__asm_flush_l3_dcache,__asm_invalidate_dcache_all,__asm_invalidate_dcache_range,__asm_invalidate_icache_all,__asm_invalidate_l3_dcache,__asm_invalidate_l3_icache,__asm_invalidate_tlb_all,__asm_switch_ttbr,armv8_el2_to_aarch32,armv8_setup_psci,armv8_switch_to_el1,armv8_switch_to_el2,flush_l3_cache,get_page_table_size,gic_init,gic_send_sgi,mmu_change_region_attr,mmu_page_table_flush,mmu_set_region_dcache_behaviour,noncached_alloc,noncached_init,protect_secure_region,psci_affinity_info,psci_arch_cpu_entry,psci_arch_init,psci_cpu_off,psci_cpu_on,psci_features,psci_features,psci_migrate_info_type,psci_setup_vectors,psci_system_off,psci_system_off,psci_system_reset,psci_system_reset,psci_system_reset2,psci_version,save_boot_params_ret,smc_call,smp_kick_all_cpus,switch_to_hypervisor_ret,wait_for_wakeup'
#for item in all.split(','):
	#doit(item + '(', 'asm/cache.h')

#all = 'srand,rand'
#for item in all.split(','):
	#doit(item + '(', 'rand.h')

#all = 'pt_regs'
#for item in all.split(','):
	#doit(item, 'asm/ptrace.h')

def run_tests(args):
    sys.argv = [sys.argv[0]] + args
    unittest.main()

def run_conversion():
    hdr = HdrConv()
    bug(hdr)
    #asm_offsets(hdr)
    hdr.run()


if __name__ == "__main__":
    parser = OptionParser()

    parser.add_option('-t', '--test', action='store_true', dest='test',
                  default=False, help='run tests')
    (options, args) = parser.parse_args()
    if options.test:
        run_tests(args)
    else:
        run_conversion()
