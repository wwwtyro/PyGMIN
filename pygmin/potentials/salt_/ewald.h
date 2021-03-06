#ifndef MINGMIN__EWALD_H
#define MINGMIN__EWALD_H

#include <complex>
#include <boost/iterator/zip_iterator.hpp>
#include <boost/tuple/tuple.hpp>
#include <boost/static_assert.hpp>
#include "vec.h"

using namespace votca::tools;

/**
 * \brief Class for ewald electrostatics
 *
 * The class calculates the k-space part of the electrostatic
 * interactions using ewald summation. Iterating over pairs for
 * the real space part has to be done by user, summing over
 * PairEnergy for all pairs.
 *
 *
 */
class Ewald
{
public:
	Ewald();

	virtual ~Ewald() {};

	/**
	 * Calculate the K-space contribution of the energy
	 *
	 * \f[
	 *   E^{(k)} = \frac{1}{2V} \sum\limits_{k \neq 0} \frac{4\pi}{k^2}e^{-k^2/4\alpha^2} | S({\bf k}) |^2
	 * \f]
	 *
	 * \param charges container/adapter for charge iteration
	 */
	template<typename container>
	double EnergyKSpace(container &charges) const;

	/**
	 * Calculate real space energy for a pair
	 */
	double PairEnergy(double r, double q) const;

	/**
	 *
	 * Calculate reals space gradient for a pair
	 */
	//double pair_gradient(const vec r_ij, vec &g) const;

	/**
	 * set the box size
	 *
	 * \param a box vector a
	 * \param b box vector b
	 * \param c box vector c
	 */
	void setBox(vec a, vec b, vec c);

	/**
	 * set the inverse width of the gaussian
	 *
	 * Set the inverse width of the gaussian. In gromacs this is called beta.
	 *
	 */
	void setAlpha(double alpha) { _alpha = alpha; }

	/***
	 *	\brief set the prefactor for coulomb interactions in MD units.
	 *
	 *	Sets the prefactor ( 1 / 4 Pi eps0)in MD units. The default
	 *	is distance in nm, charges in e and energies in kJ/mol
	 *
	 *	\parameter f prefactor in md units
	 *
	 */
	void setPrefactor(double f=138.9354859) { _f = f; }

        /**
         * set cutoff for k-space summation
         */
        void setKCut(double kcut) { _kcut = kcut;}

	/**
	 * class to zip two vectors, 1 for positions, 1 for charges
	 *
	 */
	class zip_vectors {
	public:
		zip_vectors(std::vector<vec> &positions, std::vector<double> &charges)
			: _positions(positions), _charges(charges) {}

		struct iterator {
			iterator();
			iterator(std::vector<vec>::iterator ipos, std::vector<double>::iterator iq)
				: _ipos(ipos), _iq(iq) {}
			iterator(const iterator &i) : _ipos(i._ipos), _iq(i._iq) {}

			iterator &operator++() {
				++_ipos; ++_iq; return *this;
			}

			iterator &operator=(const iterator &i) {
				_ipos = i._ipos; _iq = i._iq; return *this;
			}

			const vec &getPos() { return *_ipos; }
			double getQ() { return *_iq; }
			bool operator!=(const iterator &i) { return i._ipos != _ipos; }
		private:
			std::vector<vec>::iterator _ipos;
			std::vector<double>::iterator _iq;
		};

		iterator begin() { return iterator(_positions.begin(), _charges.begin()); }
		iterator end() { return iterator(_positions.end(), _charges.end()); }

	private:
		std::vector<vec> &_positions;
		std::vector<double> &_charges;
	};
	double _f;

	/**
	 * \brief access policy to get position and charge from container iterator
	 *
	 * The access policy allows for a general interface. Use template specialization
	 * to define how to access containers. Not defining a template specialization
	 * for a container results in a compile time assert.
	 *
	 */
	template <typename container>
	class access_policy {
	public:
		//BOOST_STATIC_ASSERT_MSG(false, "Ewald: access policy for container not defined");
		/// how to get position from iterator
		inline static const vec &r(const typename container::iterator &i);
		/// how to get charge from iterator
		inline static double &q(const typename container::iterator &i);
	};

protected:
	double _alpha;

	// reciprocal lattice vectors
	vec _ar, _br, _cr;
	// box volume
	double _V;

	// k-space cut-off
	int _lmax, _mmax, _nmax;
        double _kcut;

	/**
	 * Calculate structure factor
	 *
	 * \f[
	 *   S({\bf k}) = \sum\limits_{j=1}^N q_j e^{i{\bf k} \dot {\bf r_j}}
	 * \f]
	 */
	template<typename container>
	std::complex<double> S(const vec &k, container &charges) const;

	template<typename container>
	double Dipolar(container &charges) const;

	/**
	 * Calculate self energy
	 *
	 * \f[
	 *   E^{(s)} = - \frac{\alpha}{\sqrt{\pi}} \sum\limits_i q_i^2
	 * \f]
	 */
	template<typename container>
	double SelfEnergy(container &charges) const;
};

inline Ewald::Ewald()
	: _alpha(1.), _V(0.0)
{
	setPrefactor();
}

inline void Ewald::setBox(vec a, vec b, vec c)
{
	_V = abs((a^b)*c);
	_ar = 2.*M_PI*b^c / _V;
	_br = 2.*M_PI*c^a / _V;
	_cr = 2.*M_PI*a^b / _V;

	// cutoff for each reciprocal vector
        _lmax = _kcut / abs(_ar);
	_mmax = _kcut / abs(_br);
	_nmax = _kcut / abs(_cr);
}


inline double Ewald::PairEnergy(double r, double q) const
{
	double z = _alpha * r;
	return _f*q/r*erfc(z);
}

template<typename container>
inline double Ewald::EnergyKSpace(container &charges) const
{
	double E = 0;

	for(int l=-_lmax; l<_lmax; ++l) {
		for(int m=-_mmax; m<_mmax; ++m) {
			for(int n=-_nmax; n<_nmax; ++n) {
				if(l == 0 && m == 0 && n == 0) continue;
				vec k = double(l)*_ar + double(m)*_br + double(n)*_cr;
				double k2 = k*k;
				std::complex<double> s=S(k, charges);
				double S2 = s.real()*s.real() + s.imag()*s.imag();
				E+= exp(-0.25*k2/(_alpha*_alpha)) / k2 * S2;
				//std::cout << "E " << E << " " << k2 << k << std::endl;
			}
		}
	}
	E = _f * 2.*M_PI/_V*E ;
	printf("\nKSPace %f\n", E);
	printf("Self %f\n", SelfEnergy(charges));
	printf("Recip %f\n", E - SelfEnergy(charges));
//	printf("Dipolar %f\n", Dipolar(charges));
	return E - SelfEnergy(charges); //+ Dipolar(charges);
}


template<typename container>
inline std::complex<double> Ewald::S(const vec &k, container &charges) const
{
	std::complex<double> S(0.,0.);
	for(typename container::iterator crg=charges.begin();
			crg!=charges.end();
			++crg) {
		S+=access_policy<container>::q(crg)*exp(complex<double>(0.,-k*access_policy<container>::r(crg)));
	}
	//std::cout << S << std::endl;
	return S;
}

template<typename container>
inline double Ewald::SelfEnergy(container &charges) const
{
	double E=0;
	for(typename container::iterator crg=charges.begin();
		crg!=charges.end(); ++crg) {
		double q = access_policy<container>::q(crg);
		E+=q*q;
//std::cout << (*crg)->getPos() << " " << q << endl;
	}
	return _f*E*_alpha/sqrt(M_PI);
}

template<typename container>
double Ewald::Dipolar(container &charges) const
{
	double E=0;
	vec d(0.,0.,0.);
	for(typename container::iterator crg=charges.begin();
		crg!=charges.end(); ++crg) {
		d += access_policy<container>::q(crg)*access_policy<container>::r(crg);
//std::cout << (*crg)->getPos() << " " << q << endl;
	}
	return 2.*M_PI/(3. * _V)*d*d;
}

template<>
class Ewald::access_policy<Ewald::zip_vectors> {
public:
	inline static const vec &r(zip_vectors::iterator &i) {return i.getPos();}
	inline static double q(zip_vectors::iterator &i) {return i.getQ();}
};

#endif
