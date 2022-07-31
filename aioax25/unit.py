#!/usr/bin/env python3

"""
Unit handling.  Optionally wraps `pint`, otherwise we just
assert numeric types and assume correct units.
"""

def checknumeric(name, value, required=False):
    """
    Assert the value is a numeric value, or throw a TypeError.
    """
    if value is None:
        if required:
            raise ValueError("%s is a required parameter" % name)
        else:
            return None

    # This will throw ValueError if it can't be converted
    return float(value)


# Optional dependency: pint (for unit conversion)
try:
    from pint import Quantity

    def convertvalue(name, quantity, units, required=False):
        """
        Assert the value is a numeric value and convert to the appropriate
        units if possible.
        """
        if (quantity is not None) and isinstance(quantity, Quantity):
            # Convert to target units, take the magnitude
            return quantity.to(units).magnitude
        else:
            # Pass through to handler
            return checknumeric(name, quantity, required=required)
except ImportError: # pragma: no cover
    class Quantity(object):
        """
        Dummy Quantity class work-alike for systems without `pint`.
        """
        def __init__(self, magnitude, units):
            self.magnitude = magnitude
            self.units = units

        def __str__(self):
            return "%r %s" % (self.magnitude, self.units)

        def __repr__(self):
            return "Quantity(magnitude=%r, units=%r)" \
                    % (self.magnitude, self.units)

        def to(self, units, *a, **kwa):
            if units == self.units:
                # No conversion required
                return self

            raise NotImplementedError(
                "Unit conversion is not implemented here.  "\
                "`pip install pint` if you want unit conversion."
            )

    def convertvalue(name, quantity, units, required=False):
        if (quantity is not None) and isinstance(quantity, Quantity):
            # Assert correct units!
            if quantity.units != units:
                raise ValueError(
                        "%s parameter must be in %s units (`pip install pint` " 
                        "for unit conversion)"\
                                % (name, units)
                )
            return quantity.magnitude
        else:
            # Pass through to handler
            return checknumeric(name, quantity, required=required)
