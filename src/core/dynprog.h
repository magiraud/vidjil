#ifndef DYNPROG_H
#define DYNPROG_H

#include <string>
#include <vector>

#include <iostream>
#include <iomanip>


#define MINUS_INF -99

using namespace std;


float identity_percent(int score);

class Cost
{
 public:
  int match;
  int mismatch;

  /**
   * @param homopolymer: if MINUS_INF => same score as indel 
   */

  // del_end -> utilise seulement pour LocalEndWithSomeDeletions
  Cost (int match, int mismatch, int indel, int del_end = 0, int homopolymer = MINUS_INF);
  Cost ();

  int insertion;
  int deletion;
  int deletion_end;
  int homopolymer;
  int substitution(char a, char b);
  //int ins(char current, char next);
  //int del(char current, char next);
  int homo2(char xa, char xb, char y);
};


ostream& operator<<(ostream& out, const Cost& cost);


/* const Cost DNA = Cost(+5, -4, -10); */
/* const Cost VDJ = Cost(+5, -8, -8, -1); */

const Cost DNA = Cost(+5, -4, -10, 0, 0);
const Cost VDJ = Cost(+5, -8, -8, -1, +5);
const Cost Identity = Cost(+1, -1, -1, 0, 0);

const Cost Homopolymers = Cost(+1, MINUS_INF, -1); // TODO: true homopolymer
const Cost IdentityToto= Cost(+1, -1, -1); // avec seuil de length-2: un homopoly xou une substituion
/* const Cost Identity = Cost(+1, 0, 0); */
const Cost IdentityDirty = Cost(+1000, -1, -1); // pour avoir une estimation de longueur de l'alignement, utilise dans compare-all
const Cost Hamming = Cost(0, -1, MINUS_INF);
const Cost Levensthein = Cost(0, -1, -1);
const Cost Cluster = Cost(+1, -4, -4, 0, 0);

//const Cost Hamming = Cost();

class DynProg
{
 public:
  enum DynProgMode {
    Local,            // partial x / partial y
    LocalEndWithSomeDeletions, // local + some deletions on __
    SemiGlobalTrans,  // start-to-partial x / partial-to-end y 
    SemiGlobal,       // complete x / partial y
    Global            // complete x / complete y
  } ;

  DynProgMode mode ;
  Cost cost;

 private:
  string x ;
  string y ;
  int m ;
  int n ;
  bool reverse_x ;
  bool reverse_y ;

 public:
  int best_score ;
  int best_i ;
  int best_j ;
  int first_i ;
  int first_j ;
  string str_back ;

  DynProg(const string &x, const string &y, DynProgMode mode, const Cost &c, const bool reverse_x=false, const bool reverse_y=false);
  ~DynProg();
  void init();
  int compute();
  void backtrack();
  void SemiGlobal_hits_threshold(vector<int> &hits, int threshold, int shift_pos, int verbose);
  string SemiGlobal_extract_best();

  friend ostream& operator<<(ostream& out, const DynProg& dp);
  
  int **S;
 private: 
  int ***B;

};

ostream& operator<<(ostream& out, const DynProg& dp);

#endif

