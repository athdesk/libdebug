from ctypes import CDLL, create_string_buffer, POINTER, c_void_p, c_int, c_long, c_char_p, get_errno, set_errno
import struct
import logging
import errno
import time

NULL = 0
PTRACE_TRACEME = 0
PTRACE_PEEKTEXT = 1
PTRACE_PEEKDATA = 2
PTRACE_PEEKUSER = 3
PTRACE_POKETEXT = 4
PTRACE_POKEDATA = 5
PTRACE_POKEUSER = 6
PTRACE_CONT = 7
PTRACE_KILL = 8
PTRACE_SINGLESTEP = 9
PTRACE_GETREGS = 12
PTRACE_SETREGS = 13
PTRACE_GETFPREGS = 14
PTRACE_SETFPREGS = 15
PTRACE_ATTACH = 16
PTRACE_DETACH = 17
PTRACE_GETFPXREGS = 18
PTRACE_SETFPXREGS = 19
PTRACE_SYSCALL = 24
PTRACE_GET_THREAD_AREA = 25
PTRACE_SET_THREAD_AREA = 26
PTRACE_SETOPTIONS = 0x4200
PTRACE_GETEVENTMSG = 0x4201
PTRACE_GETSIGINFO = 0x4202
PTRACE_SETSIGINFO = 0x4203
PTRACE_INTERRUPT =  0x4207
PTRACE_O_TRACESYSGOOD        = 0x00000001
PTRACE_O_TRACEFORK        = 0x00000002
PTRACE_O_TRACEVFORK   = 0x00000004
PTRACE_O_TRACECLONE        = 0x00000008
PTRACE_O_TRACEEXEC        = 0x00000010
PTRACE_O_TRACEVFORKDONE = 0x00000020
PTRACE_O_TRACEEXIT        = 0x00000040
PTRACE_O_MASK                = 0x0000007f
PTRACE_EVENT_FORK        = 1
PTRACE_EVENT_VFORK        = 2
PTRACE_EVENT_CLONE        = 3
PTRACE_EVENT_EXEC        = 4
PTRACE_EVENT_VFORK_DONE = 5,
PTRACE_EVENT_EXIT        = 6

PTRACE_GET_SYSCALL_INFO = 0x420e

WNOHANG = 1


# /* If WIFEXITED(STATUS), the low-order 8 bits of the status.  */
def WEXITSTATUS(status):
    return (((status) & 0xff00) >> 8)

# /* If WIFSIGNALED(STATUS), the terminating signal.  */
def WTERMSIG(status):
    return ((status) & 0x7f)

# /* If WIFSTOPPED(STATUS), the signal that stopped the child.  */
def WSTOPSIG(status):
    return WEXITSTATUS(status)

# /* Nonzero if STATUS indicates normal termination.  */
def WIFEXITED(status):
    return (WTERMSIG(status) == 0)

# /* Nonzero if STATUS indicates termination by a signal.  */
def WIFSIGNALED(status):
    return (((((status) & 0x7f) + 1) >> 1) > 0) #TODO convert to signed char

# /* Nonzero if STATUS indicates the child is stopped.  */
def WIFSTOPPED(status):
    return (((status) & 0xff) == 0x7f)
class PtraceFail(Exception):
    pass


class Ptrace():
    def __init__(self):
        self.libc = CDLL("libc.so.6", use_errno=True)
        self.args_ptr = [c_int, c_long, c_long, c_char_p]
        self.args_int = [c_int, c_long, c_long, c_long]
        self.libc.ptrace.argtypes = self.args_ptr
        self.libc.ptrace.restype = c_long
        self.buf = create_string_buffer(1000)


    def waitpid(self, tid, buf, options):
        return self.libc.waitpid(tid, buf, options)

    def setregs(self, tid, data):
        bdata = create_string_buffer(data)
        self.libc.ptrace.argtypes = self.args_ptr
        if (self.libc.ptrace(PTRACE_SETREGS, tid, NULL, bdata) == -1):
            raise PtraceFail("SetRegs Failed. Do you have permisio? Running as sudo?")


    def getregs(self, tid):
        buf = create_string_buffer(1000)
        self.libc.ptrace.argtypes = self.args_ptr
        set_errno(0)
        if (self.libc.ptrace(PTRACE_GETREGS, tid, NULL, buf) == -1):
            return None

        return buf


    def setfpregs(self, tid, data):
        bdata = create_string_buffer(data)
        self.libc.ptrace.argtypes = self.args_ptr
        if (self.libc.ptrace(PTRACE_SETFPREGS, tid, NULL, bdata) == -1):
            raise PtraceFail("SetRegs Failed. Do you have permisio? Running as sudo?")


    def getfpregs(self, tid):
        buf = create_string_buffer(1000)
        self.libc.ptrace.argtypes = self.args_ptr
        set_errno(0)
        if (self.libc.ptrace(PTRACE_GETFPREGS, tid, NULL, self.buf) == -1):
            return None
        return buf


    def singlestep(self, tid):
        self.libc.ptrace.argtypes = self.args_int
        if (self.libc.ptrace(PTRACE_SINGLESTEP, tid, NULL, NULL) == -1):
            raise PtraceFail("Step Failed. Do you have permisions? Running as sudo?")


    def cont(self, tid):
        self.libc.ptrace.argtypes = self.args_int
        if (self.libc.ptrace(PTRACE_CONT, tid, NULL, NULL) == -1):
            raise PtraceFail("[%d] Continue Failed. Do you have permisions? Running as sudo?" % tid)


    def poke(self, tid, addr, value):
        set_errno(0)
        self.libc.ptrace.argtypes = self.args_int
        data = self.libc.ptrace(PTRACE_POKEDATA, tid, addr, value)

        # This errno is a libc artifact. The syscall return errno as return value and the value in the data parameter
        # We may considere to do direct syscall to avoid errno of libc
        err = get_errno()
        if err == errno.EIO:
            raise PtraceFail("Poke Failed. Are you accessing a valid address?")


    def peek(self, tid, addr):
        set_errno(0)
        self.libc.ptrace.argtypes = self.args_int
        data = self.libc.ptrace(PTRACE_PEEKDATA, tid, addr, NULL)

        # This errno is a libc artifact. The syscall return errno as return value and the value in the data parameter
        # We may considere to do direct syscall to avoid errno of libc
        err = get_errno()
        if err == errno.EIO:
            raise PtraceFail("Peek Failed. Are you accessing a valid address?")
        return data


    def setoptions(self, tid, options):
        self.libc.ptrace.argtypes = self.args_int
        r = self.libc.ptrace(PTRACE_SETOPTIONS, tid, NULL, options)
        if (r == -1):
            raise PtraceFail("Option Setup Failed. Do you have permisions? Running as sudo?")


    def attach(self, tid):
        self.libc.ptrace.argtypes = self.args_int
        set_errno(0)
        r = self.libc.ptrace(PTRACE_ATTACH, tid, NULL, NULL)
        logging.debug("attached %d", r)
        if (r == -1):
            err = get_errno()
            raise PtraceFail("Attach Failed. Err:%d Do you have permisions? Running as sudo?" % err)


    def detach(self, tid):
        self.libc.ptrace.argtypes = self.args_int
        if (self.libc.ptrace(PTRACE_DETACH, tid, NULL, NULL) == -1):
            raise PtraceFail("Detach Failed. Do you have permisio? Running as sudo?")


    def traceme(self):
        self.libc.ptrace.argtypes = self.args_int
        r = self.libc.ptrace(PTRACE_TRACEME, NULL, NULL, NULL)

    #USER struct
    def poke_user(self, tid, addr, value):
        set_errno(0)
        self.libc.ptrace.argtypes = self.args_int
        data = self.libc.ptrace(PTRACE_POKEUSER, tid, addr, value)

        # This errno is a libc artifact. The syscall return errno as return value and the value in the data parameter
        # We may considere to do direct syscall to avoid errno of libc
        err = get_errno()
        if err == errno.EIO:
            raise PtraceFail("Poke User Failed. Are you accessing a valid address?")


    def peek_user(self, tid, addr):
        set_errno(0)
        self.libc.ptrace.argtypes = self.args_int
        data = self.libc.ptrace(PTRACE_PEEKUSER, tid, addr, NULL)

        # This errno is a libc artifact. The syscall return errno as return value and the value in the data parameter
        # We may considere to do direct syscall to avoid errno of libc
        err = get_errno()
        if err == errno.EIO:
            raise PtraceFail("Peek User Failed. Are you accessing a valid address?")
        return data
    
    def syscall(self, tid):
        self.libc.ptrace.argtypes = self.args_int
        set_errno(0)
        if (self.libc.ptrace(PTRACE_SYSCALL, tid, NULL, NULL) == -1):
            time.sleep(0.01) # dirty hack, ptrace is kinda broken
            # if (self.libc.ptrace(PTRACE_SYSCALL, tid, NULL, NULL) == -1):
            #     err = get_errno()
            #     raise PtraceFail(f"PtraceSyscall Failed with {err}. Do you have permissions? Running as sudo?")
        
    def get_syscall_info(self, tid):
        """
        retval is a tuple of (syscall_id, syscall_args[6], op) if entering syscall / seccomp trap
        retval is (syscall_rval, junk[6], op) if exiting syscall
        """
        buf = create_string_buffer(128)
        for i in range(128):
            buf[i] = b"\x00"
        self.libc.ptrace.argtypes = self.args_ptr
        if (self.libc.ptrace(PTRACE_GET_SYSCALL_INFO, tid, 128, buf) == -1):
                raise PtraceFail("GetSyscallInfo Failed. Do you have permissions? Running as sudo?")
        
        if buf[0] == b"\x00": # PTRACE_SYSCALL_INFO_NONE
            return None
        else:
            id = struct.unpack("Q", buf[24:32])[0]
            args = struct.unpack("QQQQQQ", buf[32:80])
            return (id, args, int(buf[0][0]))

        # define PTRACE_SYSCALL_INFO_NONE	0
        # define PTRACE_SYSCALL_INFO_ENTRY	1
        # define PTRACE_SYSCALL_INFO_EXIT	2
        # define PTRACE_SYSCALL_INFO_SECCOMP	3
        # struct ptrace_syscall_info {
        #     __u8 op;	/* PTRACE_SYSCALL_INFO_* */
        #     __u8 pad[3];
        #     __u32 arch;
        #     __u64 instruction_pointer;
        #     __u64 stack_pointer;
        #     union {
        #         struct {
        #             __u64 nr;
        #             __u64 args[6];
        #         } entry;
        #         struct {
        #             __s64 rval;
        #             __u8 is_error;
        #         } exit;
        #         struct {
        #             __u64 nr;
        #             __u64 args[6];
        #             __u32 ret_data;
        #         } seccomp;
        #     };
        # };


AMD64_REGS = ["r15", "r14", "r13", "r12", "rbp", "rbx", "r11", "r10", "r9", "r8", "rax", "rcx", "rdx", "rsi", "rdi", "orig_rax", "rip", "cs", "eflags", "rsp", "ss", "fs_base", "gs_base", "ds", "es", "fs", "gs"]
FPREGS_SHORT = ["cwd", "swd", "ftw", "fop"]
FPREGS_LONG  = ["rip", "rdp"]
FPREGS_INT   = ["mxcsr", "mxcr_mask"]
FPREGS_80    = ["st%d" %i for i in range(8)]
FPREGS_128   = ["xmm%d" %i for i in range(16)]
AMD64_DBGREGS_OFF = {'DR0': 0x350, 'DR1': 0x358, 'DR2': 0x360, 'DR3': 0x368, 'DR4': 0x370, 'DR5': 0x378, 'DR6': 0x380, 'DR7': 0x388}
AMD64_DBGREGS_CTRL_LOCAL = {'DR0': 1<<0, 'DR1': 1<<2, 'DR2': 1<<4, 'DR3': 1<<6}
AMD64_DBGREGS_CTRL_COND  = {'DR0': 16, 'DR1': 20, 'DR2': 24, 'DR3': 28}
AMD64_DBGREGS_CTRL_COND_VAL  = {'X': 0, 'W': 1, 'IO': 2, 'RW': 3}
AMD64_DBGREGS_CTRL_LEN   = {'DR0': 18, 'DR1': 22, 'DR2': 26, 'DR3': 30}
AMD64_DBGREGS_CTRL_LEN_VAL  = {1: 0, 2: 1, 8: 2, 4: 3}
