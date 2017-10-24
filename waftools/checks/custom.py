from waftools import inflector
from waftools.checks.generic import *
from waflib import Utils
import os

__all__ = ["check_pthreads", "check_iconv", "check_lua", "check_cocoa",
        "check_openal", "check_rpi", "check_wl_protocols"]

pthreads_program = load_fragment('pthreads.c')

def check_pthread_flag(ctx, dependency_identifier):
    checks = [
        check_cc(fragment = pthreads_program, cflags = '-pthread'),
        check_cc(fragment = pthreads_program, cflags = '-pthread',
                                            linkflags = '-pthread') ]

    for fn in checks:
        if fn(ctx, dependency_identifier):
            return True
    return False

def check_pthreads(ctx, dependency_identifier):
    if ctx.dependency_satisfied('win32-internal-pthreads'):
        h = ctx.path.find_node('osdep/win32/include').abspath()
        # define IN_WINPTHREAD to workaround mingw stupidity (we never want it
        # to define features specific to its own pthread stuff)
        ctx.env.CFLAGS += ['-isystem', h, '-I', h, '-DIN_WINPTHREAD']
        return True
    if check_pthread_flag(ctx, dependency_identifier):
        return True
    platform_cflags = {
        'linux':   '-D_REENTRANT',
        'freebsd': '-D_THREAD_SAFE',
        'netbsd':  '-D_THREAD_SAFE',
        'openbsd': '-D_THREAD_SAFE',
    }.get(ctx.env.DEST_OS, '')
    libs    = ['pthreadGC2', 'pthread']
    checkfn = check_cc(fragment=pthreads_program, cflags=platform_cflags)
    checkfn_nocflags = check_cc(fragment=pthreads_program)
    for fn in [checkfn, checkfn_nocflags]:
        if check_libs(libs, fn)(ctx, dependency_identifier):
            return True
    return False

def check_iconv(ctx, dependency_identifier):
    iconv_program = load_fragment('iconv.c')
    libdliconv = " ".join(ctx.env.LIB_LIBDL + ['iconv'])
    libs       = ['iconv', libdliconv]
    args       = {'fragment': iconv_program}
    if ctx.env.DEST_OS == 'openbsd' or ctx.env.DEST_OS == 'freebsd':
        args['cflags'] = '-I/usr/local/include'
        args['linkflags'] = '-L/usr/local/lib'
    elif ctx.env.DEST_OS == 'win32':
        args['linkflags'] = " ".join(['-L' + x for x in ctx.env.LIBRARY_PATH])
    checkfn = check_cc(**args)
    return check_libs(libs, checkfn)(ctx, dependency_identifier)

def check_lua(ctx, dependency_identifier):
    lua_versions = [
        ( '51',     'lua >= 5.1.0 lua < 5.2.0'),
        ( '51obsd', 'lua51 >= 5.1.0'), # OpenBSD
        ( '51deb',  'lua5.1 >= 5.1.0'), # debian
        ( '51fbsd', 'lua-5.1 >= 5.1.0'), # FreeBSD
        ( '52',     'lua >= 5.2.0 lua < 5.3.0' ),
        ( '52arch', 'lua52 >= 5.2.0'), # Arch
        ( '52deb',  'lua5.2 >= 5.2.0'), # debian
        ( '52fbsd', 'lua-5.2 >= 5.2.0'), # FreeBSD
        ( 'luajit', 'luajit >= 2.0.0' ),
    ]

    if ctx.options.LUA_VER:
        lua_versions = \
            [lv for lv in lua_versions if lv[0] == ctx.options.LUA_VER]

    for lua_version, pkgconfig_query in lua_versions:
        if check_pkg_config(pkgconfig_query, uselib_store=lua_version) \
            (ctx, dependency_identifier):
            # XXX: this is a bit of a hack, ask waf developers if I can copy
            # the uselib_store to 'lua'
            ctx.mark_satisfied(lua_version)
            ctx.add_optional_message(dependency_identifier,
                                     'version found: ' + lua_version)
            return True
    return False

def check_wl_protocols(ctx, dependency_identifier):
    def fn(ctx, dependency_identifier):
        ret = check_pkg_config_datadir("wayland-protocols")
        ret = ret(ctx, dependency_identifier)
        if ret != None:
            ctx.env.WL_PROTO_DIR = ret.split()[0]
        return ret
    return fn(ctx, dependency_identifier)

def check_cocoa(ctx, dependency_identifier):
    fn = check_cc(
        fragment         = load_fragment('cocoa.m'),
        compile_filename = 'test.m',
        framework_name   = ['Cocoa', 'IOKit', 'OpenGL', 'QuartzCore'],
        includes         = ctx.srcnode.abspath(),
        linkflags        = '-fobjc-arc')

    return fn(ctx, dependency_identifier)

def check_openal(ctx, dependency_identifier):
    checks = [
        check_pkg_config('openal', '>= 1.13'),
        check_statement(['OpenAL/AL.h'], 'int i = AL_VERSION', framework='OpenAL')
        ]

    for fn in checks:
        if fn(ctx, dependency_identifier):
            return True
    return False

def check_rpi(ctx, dependency_identifier):
    # We need MMAL/bcm_host/dispmanx APIs.
    # Upstream keeps pkgconfig files in '/opt/vc/lib/pkgconfig'.
    # See https://github.com/raspberrypi/userland/issues/245
    # PKG_CONFIG_SYSROOT_DIR helps with cross compilation.
    prev_pkg_path = os.getenv('PKG_CONFIG_PATH', '')
    os.environ['PKG_CONFIG_PATH'] = os.pathsep.join(
        filter(None, [os.path.join(os.getenv('PKG_CONFIG_SYSROOT_DIR', '/'),
                                   'opt/vc/lib/pkgconfig'),
                      prev_pkg_path]))

    checks = [
        # We still need all OpenGL symbols, because the vo_opengl code is
        # generic and supports anything from GLES2/OpenGL 2.1 to OpenGL 4 core.
        check_pkg_config('bcm_host', uselib_store='bcm_host'),
        check_pkg_config('egl'),
        check_pkg_config('glesv2'),
        check_cc(lib=['mmal_core', 'mmal_util', 'mmal_vc_client'], use=['bcm_host']),
    ]

    ret = all((fn(ctx, dependency_identifier) for fn in checks))
    os.environ['PKG_CONFIG_PATH'] = prev_pkg_path
    return ret
