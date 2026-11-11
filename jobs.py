"""Prisma - job di conversione e worker in background."""
from __future__ import annotations

import itertools
import os
import time
from PySide6.QtCore import QObject, QRunnable, Signal

import engine


_ids = itertools.count(1)


class Job:
    def __init__(self, path, rel="", temp=False):
        self.id = next(_ids)
        self.path = path
        self.rel = rel
        self.temp = temp
        self.name = os.path.basename(path)
        self.ext = engine.ext_of(path)
        try:
            self.size = os.path.getsize(path)
        except OSError:
            self.size = 0
        self.w = self.h = 0
        self.fmt = self.ext.upper()
        self.alpha = False
        self.frames = 1
        self.thumb = None
        self.probed = False
        self.probe_error = None
        self.status = "pending"
        self.out = None
        self.outs = []
        self.out_size = 0
        self.msg = ""
        self.elapsed = 0.0
        self.target = None

    def snapshot(self):
        return dict(path=self.path, rel=self.rel, w=self.w, h=self.h, alpha=self.alpha, frames=self.frames)


class Emitter(QObject):
    probed = Signal(int, object)
    started = Signal(int)
    done = Signal(int, object)
    preview = Signal(str, object)
    message = Signal(str)


class ProbeTask(QRunnable):
    def __init__(self, job_id, path, tools, emitter, size=160, kind="probe"):
        super().__init__()
        self.job_id, self.path, self.tools, self.emitter, self.size, self.kind = job_id, path, tools, emitter, size, kind

    def run(self):
        try:
            info = engine.probe(self.path, self.tools, self.size)
        except Exception as e:  # noqa
            info = dict(w=0, h=0, fmt="", alpha=False, frames=1, thumb=None, error=str(e))
        if self.kind == "preview":
            self.emitter.preview.emit(self.path, info)
        else:
            self.emitter.probed.emit(self.job_id, info)


class ConvertTask(QRunnable):
    def __init__(self, job_id, snap, settings, tools, emitter, cancel, index, tpj):
        super().__init__()
        self.job_id, self.snap, self.s, self.tools = job_id, snap, settings, tools
        self.emitter, self.cancel, self.index, self.tpj = emitter, cancel, index, tpj

    def run(self):
        if self.cancel.is_set():
            self.emitter.done.emit(self.job_id, dict(status="cancelled", msg="Annullato"))
            return
        self.emitter.started.emit(self.job_id)
        t0 = time.perf_counter()
        try:
            res = engine.convert(self.snap, self.s, self.tools, self.cancel, self.index, self.tpj)
        except engine.Cancelled:
            res = dict(status="cancelled", msg="Annullato")
        except engine.ConvertError as e:
            res = dict(status="error", msg=str(e))
        except Exception as e:  # noqa
            res = dict(status="error", msg=f"{type(e).__name__}: {e}")
        res["elapsed"] = time.perf_counter() - t0
        self.emitter.done.emit(self.job_id, res)
