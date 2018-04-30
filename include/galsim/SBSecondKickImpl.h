/* -*- c++ -*-
 * Copyright (c) 2012-2018 by the GalSim developers team on GitHub
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

#ifndef GalSim_SBSecondKickImpl_H
#define GalSim_SBSecondKickImpl_H

#include "SBProfileImpl.h"
#include "SBSecondKick.h"
#include "LRUCache.h"
#include "OneDimensionalDeviate.h"
#include "Table.h"
#include "SBAiryImpl.h"
#include <boost/move/unique_ptr.hpp>

namespace galsim {

    //
    //
    //
    //SKInfo
    //
    //
    //

    class SKInfo
    {
    public:
        SKInfo(double kcrit, const GSParamsPtr& gsparams);
        ~SKInfo() {}

        double stepK() const { return _stepk; }
        double maxK() const { return _maxk; }
        double getDelta() const { return _delta; }

        double kValue(double) const;
        double kValueRaw(double) const;
        double xValue(double) const;
        double xValueRaw(double) const;
        double xValueExact(double) const;
        double structureFunction(double rho) const;
        boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const;

    private:
        SKInfo(const SKInfo& rhs); ///<Hide the copy constructor
        void operator=(const SKInfo& rhs); ///<Hide the assignment operator

        double _kcrit;
        double _stepk;
        double _maxk;
        double _delta;

        const GSParamsPtr _gsparams;

        TableDD _radial;
        TableDD _kvLUT;
        boost::shared_ptr<OneDimensionalDeviate> _sampler;

        void _buildRadial();
        void _buildKVLUT();
    };

    //
    //
    //
    //SBSecondKickImpl
    //
    //
    //

    class SBSecondKick::SBSecondKickImpl : public SBProfileImpl
    {
    public:
        SBSecondKickImpl(double lam_over_r0, double kcrit, double flux,
                         const GSParamsPtr& gsparams);
        ~SBSecondKickImpl() {}

        bool isAxisymmetric() const { return true; }
        bool hasHardEdges() const { return false; }
        bool isAnalyticX() const { return false; }
        bool isAnalyticK() const { return true; }

        double maxK() const;
        double stepK() const;
        double getDelta() const;

        Position<double> centroid() const { return Position<double>(0., 0.); }

        double getFlux() const { return _flux-getDelta(); }
        double getLamOverR0() const { return _lam_over_r0; }
        double getKCrit() const { return _kcrit; }
        double maxSB() const { return _flux * _info->xValue(0.); }

        /**
         * @brief SBSecondKick photon-shooting is done numerically with `OneDimensionalDeviate`
         * class.
         *
         * @param[in] N Total number of photons to produce.
         * @param[in] ud UniformDeviate that will be used to draw photons from distribution.
         * @returns PhotonArray containing all the photons' info.
         */
        boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const;

        double xValue(const Position<double>& p) const;
        double xValue(double r) const;
        double xValueRaw(double k) const;
        double xValueExact(double k) const;
        std::complex<double> kValue(const Position<double>& p) const;
        double kValue(double k) const;
        double kValueRaw(double k) const;

        double structureFunction(double rho) const;

        std::string serialize() const;

    private:

        double _lam_over_r0;
        double _k0;
        double _inv_k0;
        double _kcrit;
        double _flux;
        double _xnorm;

        boost::shared_ptr<SKInfo> _info;

        // Copy constructor and op= are undefined.
        SBSecondKickImpl(const SBSecondKickImpl& rhs);
        void operator=(const SBSecondKickImpl& rhs);

        static LRUCache<boost::tuple<double,GSParamsPtr>,SKInfo> cache;
    };
}

#endif