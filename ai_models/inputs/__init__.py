# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
from functools import cached_property

import earthkit.data as ekd

LOG = logging.getLogger(__name__)


class RequestBasedInput:
    def __init__(self, owner, **kwargs):
        self.owner = owner

    def _patch(self, **kargs):
        r = dict(**kargs)
        self.owner.patch_retrieve_request(r)
        return r

    @cached_property
    def fields_sfc(self):
        param = self.owner.param_sfc
        if not param:
            return cml.load_source("empty")

        LOG.info(f"Loading surface fields from {self.WHERE}")

        return ekd.from_source(
            "multi",
            [
                self.sfc_load_source(
                    **self._patch(
                        date=date,
                        time=time,
                        param=param,
                        grid=self.owner.grid,
                        area=self.owner.area,
                        **self.owner.retrieve,
                    )
                )
                for date, time in self.owner.datetimes()
            ],
        )

    @cached_property
    def fields_pl(self):
        param, level = self.owner.param_level_pl
        if not (param and level):
            return cml.load_source("empty")

        LOG.info(f"Loading pressure fields from {self.WHERE}")
        return ekd.from_source(
            "multi",
            [
                self.pl_load_source(
                    **self._patch(
                        date=date,
                        time=time,
                        param=param,
                        level=level,
                        grid=self.owner.grid,
                        area=self.owner.area,
                    )
                )
                for date, time in self.owner.datetimes()
            ],
        )

    @cached_property
    def fields_ml(self):
        param, level = self.owner.param_level_ml
        if not (param and level):
            return cml.load_source("empty")

        LOG.info(f"Loading model fields from {self.WHERE}")
        return ekd.from_source(
            "multi",
            [
                self.ml_load_source(
                    **self._patch(
                        date=date,
                        time=time,
                        param=param,
                        level=level,
                        grid=self.owner.grid,
                        area=self.owner.area,
                    )
                )
                for date, time in self.owner.datetimes()
            ],
        )

    @cached_property
    def all_fields(self):
        return self.fields_sfc + self.fields_pl + self.fields_ml


class MarsInput(RequestBasedInput):
    WHERE = "MARS"

    def __init__(self, owner, **kwargs):
        self.owner = owner

    def pl_load_source(self, **kwargs):
        kwargs["levtype"] = "pl"
        logging.debug("load source mars %s", kwargs)
        return ekd.from_source("mars", kwargs)

    def sfc_load_source(self, **kwargs):
        kwargs["levtype"] = "sfc"
        logging.debug("load source mars %s", kwargs)
        return ekd.from_source("mars", kwargs)

    def ml_load_source(self, **kwargs):
        kwargs["levtype"] = "ml"
        logging.debug("load source mars %s", kwargs)
        return ekd.from_source("mars", kwargs)


class CdsInput(RequestBasedInput):
    WHERE = "CDS"

    def pl_load_source(self, **kwargs):
        kwargs["product_type"] = "reanalysis"
        return ekd.from_source("cds", "reanalysis-era5-pressure-levels", kwargs)

    def sfc_load_source(self, **kwargs):
        kwargs["product_type"] = "reanalysis"
        return ekd.from_source("cds", "reanalysis-era5-single-levels", kwargs)

    def ml_load_source(self, **kwargs):
        raise NotImplementedError("CDS does not support model levels")


class FileInput:
    def __init__(self, owner, file, **kwargs):
        self.file = file
        self.owner = owner

    @cached_property
    def fields_sfc(self):
        return self.all_fields.sel(levtype="sfc")

    @cached_property
    def fields_pl(self):
        return self.all_fields.sel(levtype="pl")

    @cached_property
    def fields_ml(self):
        return self.all_fields.sel(levtype="ml")

    @cached_property
    def all_fields(self):
        return ekd.from_source("file", self.file)


INPUTS = dict(
    mars=MarsInput,
    file=FileInput,
    cds=CdsInput,
)


def get_input(name, *args, **kwargs):
    return INPUTS[name](*args, **kwargs)


def available_inputs():
    return sorted(INPUTS.keys())
