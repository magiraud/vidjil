#ifndef SEGMENT_H
#define SEGMENT_H

#include <string>
#include <iostream>
#include "fasta.h"
#include "dynprog.h"
#include "tools.h"
#include "kmerstore.h"
#include "kmeraffect.h"

using namespace std;

enum SEGMENTED { DONT_KNOW, SEG_PLUS, SEG_MINUS, UNSEG_TOO_SHORT, UNSEG_STRAND_NOT_CONSISTENT, 
		 UNSEG_TOO_FEW_ZERO,  UNSEG_TOO_FEW_V, UNSEG_TOO_FEW_J, 
		 UNSEG_BAD_DELTA_MIN, UNSEG_BAD_DELTA_MAX, STATS_SIZE } ;
const char* const segmented_mesg[] = { "?", "+", "-", "UNSEG too short", "UNSEG strand",  
				       "UNSEG too few (zero)", "UNSEG too few V", "UNSEG too few J",
				       "UNSEG < delta_min", "UNSEG > delta_max" } ;

class Segmenter {
protected:
  string label;
  string sequence;
  int left, right;
  int left2, right2;
  bool reversed, segmented, dSegmented;

  string removeChevauchement();
  bool finishSegmentation();
  bool finishSegmentationD();

 public:
  string code;
  string code_light;
  string info;
  int best_V, best_J ;
  int del_V, del_D_left, del_D_right, del_J ;
  string seg_V, seg_N, seg_J;
  
  int best_D;
  string seg_N1, seg_D, seg_N2;

  /* Queries */



  bool html(ostream &out, int flag_D);

  Sequence getSequence() const ;

  /**
   * @param l: length around the junction
   * @return the string centered on the junction (ie. at position
   *         (getLeft() + getRight())/2).
   *         The string has length l unless the original string 
   *         is not long enough.
   *         The junction is revcomp-ed if the original string comes from reverse
   *         strand.
   */
  string getJunction(int l) const;

  /**
   * @return the left position (on forward strand) of the segmentation.
   */
  int getLeft() const;
  
  /**
   * @return the right position (on forward strand) of the segmentation
   */
  int getRight() const;
  
  /**
   * @return the left position (on forward strand) of the D segmentation.
   */
  int getLeftD() const;
  
  /**
   * @return the right position (on forward strand) of the D segmentation
   */
  int getRightD() const;


  /**
   * @return true iff the string comes from reverse strand
   */
  bool isReverse() const;

  /**
   * @return true iff the sequence has been successfully segmented
   */
  bool isSegmented() const;
  
  /**
   * @return true if a D gene was found in the N region
   */
  bool isDSegmented() const;


  friend ostream &operator<<(ostream &out, const Segmenter &s);
};



ostream &operator<<(ostream &out, const Segmenter &s);



class KmerSegmenter : public Segmenter
{
 protected:
  string affects;

 public:
  /**
   * Build a segmenter based on KmerSegmentation
   * @param seq: An object read from a FASTA/FASTQ file
   * @param index: A Kmer index
   * @param delta_min: the minimal distance between the right bound and the left bound 
   *        so that the segmentation is accepted 
   *        (left bound: end of V, right bound : start of J)
   * @param delta_min: the maximal distance between the right bound and the left bound 
   *        so that the segmentation is accepted 
   *        (left bound: end of V, right bound : start of J)
   * @param stats: integer array (of size STATS_SIZE) to store statistics
   */
  KmerSegmenter(Sequence seq, IKmerStore<KmerAffect> *index, int delta_min, int delta_max, int *stats);
};

class FineSegmenter : public Segmenter
{
 public:
   /**
   * Build a fineSegmenter based on KmerSegmentation
   * @param seq: An object read from a FASTA/FASTQ file
   * @param rep_V: germline for V
   * @param rep_J: germline for J
   * @param delta_min: the minimal distance between the right bound and the left bound 
   *        so that the segmentation is accepted 
   *        (left bound: end of V, right bound : start of J)
   * @param delta_min: the maximal distance between the right bound and the left bound 
   *        so that the segmentation is accepted 
   *        (left bound: end of V, right bound : start of J)
   */
  FineSegmenter(Sequence seq, Fasta &rep_V, Fasta &rep_J, int delta_min, int delta_max);
  
  /**
  * extend segmentation from VJ to VDJ
  * @param rep_J: germline for V
  * @param rep_J: germline for D
  * @param rep_J: germline for J
  */
  void FineSegmentD(Fasta &rep_V, Fasta &rep_D, Fasta &rep_J);
};



#endif
