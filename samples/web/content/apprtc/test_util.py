# Copyright 2014 Google Inc. All Rights Reserved.
#
# Utilities for unit tests.

class ReplaceFunction(object):
  """Makes it easier to replace a function in a class or module."""
  def __init__(self, obj, function_name, new_function):
    self.obj = obj
    self.function_name = function_name
    self.old_function = getattr(self.obj, self.function_name)
    setattr(self.obj, self.function_name, new_function)

  def __del__(self):
    setattr(self.obj, self.function_name, self.old_function)

class CapturingFunction(object):
  """Captures the last arguments called on a function."""
  def __init__(self, retValue=None):
    self.retValue = retValue
    self.lastArgs = None
    self.lastKwargs = None

  def __call__(self, *args, **kwargs):
    self.lastArgs = args
    self.lastKwargs = kwargs

    if callable(self.retValue):
      return self.retValue()

    return self.retValue
