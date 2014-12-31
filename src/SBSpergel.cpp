/* -*- c++ -*-
 * Copyright (c) 2012-2014 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

//#define DEBUGLOGGING

#include "SBSpergel.h"
#include "SBSpergelImpl.h"
#include <boost/math/special_functions/bessel.hpp>
#include <boost/math/special_functions/gamma.hpp>
#include "Solve.h"

// Define this variable to find azimuth (and sometimes radius within a unit disc) of 2d photons by
// drawing a uniform deviate for theta, instead of drawing 2 deviates for a point on the unit
// circle and rejecting corner photons.
// The relative speed of the two methods was tested as part of issue #163, and the results
// are collated in devutils/external/time_photon_shooting.
// The conclusion was that using sin/cos was faster for icpc, but not g++ or clang++.
#ifdef _INTEL_COMPILER
#define USE_COS_SIN
#endif

#ifdef DEBUGLOGGING
#include <fstream>
#endif

namespace galsim {

    SBSpergel::SBSpergel(double nu, double size, RadiusType rType, double flux,
                         const GSParamsPtr& gsparams) :
        SBProfile(new SBSpergelImpl(nu, size, rType, flux, gsparams)) {}

    SBSpergel::SBSpergel(const SBSpergel& rhs) : SBProfile(rhs) {}

    SBSpergel::~SBSpergel() {}

    double SBSpergel::getNu() const
    {
        assert(dynamic_cast<const SBSpergelImpl*>(_pimpl.get()));
        return static_cast<const SBSpergelImpl&>(*_pimpl).getNu();
    }

    double SBSpergel::getScaleRadius() const
    {
        assert(dynamic_cast<const SBSpergelImpl*>(_pimpl.get()));
        return static_cast<const SBSpergelImpl&>(*_pimpl).getScaleRadius();
    }

    double SBSpergel::getHalfLightRadius() const
    {
        assert(dynamic_cast<const SBSpergelImpl*>(_pimpl.get()));
        return static_cast<const SBSpergelImpl&>(*_pimpl).getHalfLightRadius();
    }

    LRUCache<boost::tuple< double, GSParamsPtr >, SpergelInfo> SBSpergel::SBSpergelImpl::cache(
        sbp::max_spergel_cache);

    SBSpergel::SBSpergelImpl::SBSpergelImpl(double nu, double size, RadiusType rType,
                                            double flux, const GSParamsPtr& gsparams) :
        SBProfileImpl(gsparams),
        _nu(nu), _flux(flux),
        _gamma_nup1(boost::math::tgamma(_nu+1.0)),
        _info(cache.get(boost::make_tuple(_nu, this->gsparams.duplicate())))
    {
        dbg<<"Start SBSpergel constructor:\n";
        dbg<<"nu = "<<_nu<<std::endl;
        dbg<<"flux = "<<_flux<<std::endl;
        dbg<<"C_nu = "<<_info->getHLR()<<std::endl;

        switch(rType) {
        case HALF_LIGHT_RADIUS:
            {
                _re = size;
                _r0 = _re / _info->getHLR();
            }
            break;
        case SCALE_RADIUS:
            {
                _r0 = size;
                _re = _r0 * _info->getHLR();
            }
            break;
        }

        _r0_sq = _r0 * _r0;
        _inv_r0 = 1. / _r0;
        _norm = _flux / _r0_sq / _gamma_nup1 / (2.0 * M_PI) / std::pow(2., _nu);

        dbg<<"scale radius = "<<_r0<<std::endl;
        dbg<<"HLR = "<<_re<<std::endl;
    }

    double SBSpergel::SBSpergelImpl::maxK() const { return _info->maxK() * _inv_r0; }
    double SBSpergel::SBSpergelImpl::stepK() const { return _info->stepK() * _inv_r0; }

    // Equations (3, 4) of Spergel (2010)
    double SBSpergel::SBSpergelImpl::xValue(const Position<double>& p) const
    {
        double r = sqrt(p.x * p.x + p.y * p.y) * _inv_r0;
        return _norm * _info->xValue(r);
    }

    // Equation (2) of Spergel (2010)
    std::complex<double> SBSpergel::SBSpergelImpl::kValue(const Position<double>& k) const
    {
        double ksq = (k.x*k.x + k.y*k.y) * _r0_sq;
        return _flux * _info->kValue(ksq);
    }

    void SBSpergel::SBSpergelImpl::fillXValue(tmv::MatrixView<double> val,
                                              double x0, double dx, int ix_zero,
                                              double y0, double dy, int iy_zero) const
    {
        dbg<<"SBSpergel fillXValue\n";
        dbg<<"x = "<<x0<<" + ix * "<<dx<<", ix_zero = "<<ix_zero<<std::endl;
        dbg<<"y = "<<y0<<" + iy * "<<dy<<", iy_zero = "<<iy_zero<<std::endl;
        if (ix_zero != 0 || iy_zero != 0) {
            xdbg<<"Use Quadrant\n";
            fillXValueQuadrant(val,x0,dx,ix_zero,y0,dy,iy_zero);
            // Spergels can be super peaky at the center, so handle explicitly like Sersics
            if (ix_zero != 0 && iy_zero != 0)
                val(ix_zero, iy_zero) = _norm * _info->xValue(0.);
        } else {
            xdbg<<"Non-Quadrant\n";
            assert(val.stepi() == 1);
            const int m = val.colsize();
            const int n = val.rowsize();
            typedef tmv::VIt<double,1,tmv::NonConj> It;

            x0 *= _inv_r0;
            dx *= _inv_r0;
            y0 *= _inv_r0;
            dy *= _inv_r0;

            for (int j=0;j<n;++j,y0+=dy) {
                double x = x0;
                double ysq = y0*y0;
                It valit = val.col(j).begin();
                for (int i=0;i<m;++i,x+=dx) {
                    double r = sqrt(x*x + ysq);
                    *valit++ = _norm * _info->xValue(r);
                }
            }
        }
    }

    void SBSpergel::SBSpergelImpl::fillKValue(tmv::MatrixView<std::complex<double> > val,
                                            double x0, double dx, int ix_zero,
                                            double y0, double dy, int iy_zero) const
    {
        dbg<<"SBSpergel fillKValue\n";
        dbg<<"x = "<<x0<<" + ix * "<<dx<<", ix_zero = "<<ix_zero<<std::endl;
        dbg<<"y = "<<y0<<" + iy * "<<dy<<", iy_zero = "<<iy_zero<<std::endl;
        if (ix_zero != 0 || iy_zero != 0) {
            xdbg<<"Use Quadrant\n";
            fillKValueQuadrant(val,x0,dx,ix_zero,y0,dy,iy_zero);
        } else {
            xdbg<<"Non-Quadrant\n";
            assert(val.stepi() == 1);
            const int m = val.colsize();
            const int n = val.rowsize();
            typedef tmv::VIt<std::complex<double>,1,tmv::NonConj> It;

            x0 *= _r0;
            dx *= _r0;
            y0 *= _r0;
            dy *= _r0;

            for (int j=0;j<n;++j,y0+=dy) {
                double x = x0;
                double ysq = y0*y0;
                It valit(val.col(j).begin().getP(),1);
                for (int i=0;i<m;++i,x+=dx) {
                    double ksq = x*x + ysq;
                    *valit++ = _flux * _info->kValue(ksq);
                }
            }
        }
    }

    void SBSpergel::SBSpergelImpl::fillXValue(tmv::MatrixView<double> val,
                                            double x0, double dx, double dxy,
                                            double y0, double dy, double dyx) const
    {
        dbg<<"SBSpergel fillXValue\n";
        dbg<<"x = "<<x0<<" + ix * "<<dx<<" + iy * "<<dxy<<std::endl;
        dbg<<"y = "<<y0<<" + ix * "<<dyx<<" + iy * "<<dy<<std::endl;
        assert(val.stepi() == 1);
        assert(val.canLinearize());
        const int m = val.colsize();
        const int n = val.rowsize();
        typedef tmv::VIt<double,1,tmv::NonConj> It;

        x0 *= _inv_r0;
        dx *= _inv_r0;
        dxy *= _inv_r0;
        y0 *= _inv_r0;
        dy *= _inv_r0;
        dyx *= _inv_r0;

        double x00 = x0; // Preserve the originals for below.
        double y00 = y0;
        It valit = val.linearView().begin();
        for (int j=0;j<n;++j,x0+=dxy,y0+=dy) {
            double x = x0;
            double y = y0;
            It valit = val.col(j).begin();
            for (int i=0;i<m;++i,x+=dx,y+=dyx) {
                double r = sqrt(x*x + y*y);
                *valit++ = _norm * _info->xValue(r);
            }
        }

        // Check for (0,0) in disguise as in Sersic
        double det = dx * dy - dxy * dyx;
        double i0 = (-dy * x00 + dxy * y00) / det;
        double j0 = (dyx * x00 - dx * y00) / det;
        dbg<<"i0, j0 = "<<i0<<','<<j0<<std::endl;
        dbg<<"x0 + dx i + dxy j = "<<x00+dx*i0+dxy*j0<<std::endl;
        dbg<<"y0 + dyx i + dy j = "<<y00+dyx*i0+dy*j0<<std::endl;
        int inti0 = int(floor(i0+0.5));
        int intj0 = int(floor(j0+0.5));

        if ( std::abs(i0 - inti0) < 1.e-12 && std::abs(j0 - intj0) < 1.e-12 &&
             inti0 >= 0 && inti0 < m && intj0 >= 0 && intj0 < n)  {
            dbg<<"Fixing central value from "<<val(inti0, intj0);
            val(inti0, intj0) = _norm * _info->xValue(0.0);
            dbg<<" to "<<val(inti0, intj0)<<std::endl;
#ifdef DEBUGLOGGING
            double x = x00;
            double y = y00;
            for (int j=0;j<intj0;++j) { x += dxy; y += dy; }
            for (int i=0;i<inti0;++i) { x += dx; y += dyx; }
            double r = sqrt(x*x+y*y);
            dbg<<"Note: the original r value for this pixel had been "<<r<<std::endl;
            dbg<<"xValue(r) = "<<_info->xValue(r)<<std::endl;
            dbg<<"xValue(0) = "<<_info->xValue(0.)<<std::endl;
#endif
        }

    }

    void SBSpergel::SBSpergelImpl::fillKValue(tmv::MatrixView<std::complex<double> > val,
                                            double x0, double dx, double dxy,
                                            double y0, double dy, double dyx) const
    {
        dbg<<"SBSpergel fillKValue\n";
        dbg<<"x = "<<x0<<" + ix * "<<dx<<" + iy * "<<dxy<<std::endl;
        dbg<<"y = "<<y0<<" + ix * "<<dyx<<" + iy * "<<dy<<std::endl;
        assert(val.stepi() == 1);
        assert(val.canLinearize());
        const int m = val.colsize();
        const int n = val.rowsize();
        typedef tmv::VIt<std::complex<double>,1,tmv::NonConj> It;

        x0 *= _r0;
        dx *= _r0;
        dxy *= _r0;
        y0 *= _r0;
        dy *= _r0;
        dyx *= _r0;

        It valit(val.linearView().begin().getP());
        for (int j=0;j<n;++j,x0+=dxy,y0+=dy) {
            double x = x0;
            double y = y0;
            It valit(val.col(j).begin().getP(),1);
            for (int i=0;i<m;++i,x+=dx,y+=dyx) {
                double ksq = x*x + y*y;
                *valit++ = _flux * _info->kValue(ksq);
            }
        }
    }

    SpergelInfo::SpergelInfo(double nu, const GSParamsPtr& gsparams) :
        _nu(nu), _gsparams(gsparams),
        _gamma_nup1(boost::math::tgamma(_nu+1.0)),
        _gamma_nup2(_gamma_nup1 * (_nu+1)),
        _cnu(calculateFluxRadius(0.5)),
        _maxk(0.), _stepk(0.), _re(0.), _flux(0.)
    {
        dbg<<"Start SpergelInfo constructor for nu = "<<_nu<<std::endl;

        if (_nu < sbp::minimum_spergel_nu || _nu > sbp::maximum_spergel_nu)
            throw SBError("Requested Spergel index out of range");
    }

    class SpergelIntegratedFlux
    {
    public:
        SpergelIntegratedFlux(double nu, double gamma_nup2, double flux_frac=0.0)
            : _nu(nu), _gamma_nup2(gamma_nup2),  _target(flux_frac) {}

        double operator()(double u) const
        // Return flux integrated up to radius `u` in units of r0, minus `flux_frac`
        // (i.e., make a residual so this can be used to search for a target flux.
        {
            double fnup1 = std::pow(u / 2., _nu+1)
                * boost::math::cyl_bessel_k(_nu+1, u)
                / _gamma_nup2;
            double f = 1.0 - 2.0 * (1+_nu)*fnup1;
            return f - _target;
        }
    private:
        double _nu;
        double _gamma_nup2;
        double _target;
    };

    double SpergelInfo::calculateFluxRadius(const double& flux_frac) const
    {
        // Calcute r such that L(r/r0) / L_tot == flux_frac

        // These seem to bracket pretty much every reasonable possibility
        // that I checked in Mathematica.
        double z1=0.001;
        double z2=25.0;
        SpergelIntegratedFlux func(_nu, _gamma_nup2, flux_frac);
        Solve<SpergelIntegratedFlux> solver(func, z1, z2);
        solver.setMethod(Brent);
        double R = solver.root();
        dbg<<"flux_frac = "<<flux_frac<<std::endl;
        dbg<<"r/r0 = "<<R<<std::endl;
        return R;
    }

    double SpergelInfo::stepK() const
    {
        if (_stepk == 0.) {
            double R = calculateFluxRadius(1.0 - _gsparams->folding_threshold);
            // Go to at least 5*re
            R = std::max(R,_gsparams->stepk_minimum_hlr/_cnu);
            _stepk = M_PI / R;
        }
        return _stepk;
    }

    double SpergelInfo::maxK() const
    {
        if(_maxk == 0.) {
            // Solving (1+k^2)^(-1-nu) = maxk_threshold for k
            // exact:
            //_maxk = std::sqrt(std::pow(gsparams->maxk_threshold, -1./(1+_nu))-1.0);
            // approximate 1+k^2 ~ k^2 => good enough:
            _maxk = std::pow(_gsparams->maxk_threshold, -1./(2*(1+_nu)));
        }
        return _maxk;
    }

    double SpergelInfo::getHLR() const
    {
        return _cnu;
    }

    double SpergelInfo::xValue(double r) const
    {
        if (r == 0.) {
            if (_nu > 0) return _gamma_nup1 / (2. * _nu) * std::pow(2., _nu);
            else return INFINITY;
        }
        return boost::math::cyl_bessel_k(_nu, r) * std::pow(r, _nu);
    }

    double SpergelInfo::kValue(double ksq) const
    {
        return std::pow(1. + ksq, -1. - _nu);
    }

    class SpergelRadialFunction: public FluxDensity
    {
    public:
        SpergelRadialFunction(double nu): _nu(nu) {}
        double operator()(double r) const { return std::exp(-std::pow(r,_nu)) * boost::math::cyl_bessel_k(_nu, r); }
    private:
        double _nu;
    };

    boost::shared_ptr<PhotonArray> SpergelInfo::shoot(int N, UniformDeviate ud) const
    {
        dbg<<"SpergelInfo shoot: N = "<<N<<std::endl;
        dbg<<"Target flux = 1.0\n";

        if (!_sampler) {
            // Set up the classes for photon shooting
            _radial.reset(new SpergelRadialFunction(_nu));
            std::vector<double> range(2,0.);
            //double shoot_maxr = calculateMissingFluxRadius(_gsparams->shoot_accuracy);
            double shoot_maxr = 1.0;
            range[1] = shoot_maxr;
            _sampler.reset(new OneDimensionalDeviate( *_radial, range, true, _gsparams));
        }

        assert(_sampler.get());
        boost::shared_ptr<PhotonArray> result = _sampler->shoot(N,ud);
        dbg<<"SpergelInfo Realized flux = "<<result->getTotalFlux()<<std::endl;
        return result;
    }

    boost::shared_ptr<PhotonArray> SBSpergel::SBSpergelImpl::shoot(int N, UniformDeviate ud) const
    {
        dbg<<"Spergel shoot: N = "<<N<<std::endl;
        dbg<<"Target flux = "<<getFlux()<<std::endl;
        // Get photons from the SpergelInfo structure, rescale flux and size for this instance
        boost::shared_ptr<PhotonArray> result = _info->shoot(N,ud);
        result->scaleFlux(_shootnorm);
        result->scaleXY(_r0);
        dbg<<"Spergel Realized flux = "<<result->getTotalFlux()<<std::endl;
        return result;
    }
}