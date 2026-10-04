"""Independent compressed Petri-net witness check using per-transition guards."""
import argparse
import json
from pathlib import Path


def check(problem, segments):
    marking=list(problem['initial'])
    for segment in segments:
        count=int(segment['repetitions'])
        if count<0 or not segment['word']:
            raise ValueError('Invalid repeated word')
        offset=[0]*len(marking)
        guards=[]
        for index in segment['word']:
            if type(index) is not int or not 0<=index<len(problem['transitions']):
                raise ValueError('Invalid transition index')
            transition=problem['transitions'][index]
            guards.extend((p,w-offset[p]) for p,w in transition['pre'])
            for p,w in transition['pre']:offset[p]-=w
            for p,w in transition['post']:offset[p]+=w
        if count:
            for p,required in guards:
                if min(marking[p],marking[p]+(count-1)*offset[p])<required:
                    raise ValueError('Disabled transition in repeated word')
            marking=[m+count*d for m,d in zip(marking,offset)]
            if any(m<0 for m in marking):raise ValueError('Negative marking')
    for constraint in problem['target']:
        value=sum(a*m for a,m in zip(constraint['coefficients'],marking))
        if not (value==constraint['bound'] if constraint['equality'] else value>=constraint['bound']):
            raise ValueError('Target not satisfied')
    return marking


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('problem',type=Path);parser.add_argument('answer',type=Path)
    args=parser.parse_args()
    problem=json.loads(args.problem.read_text());answer=json.loads(args.answer.read_text())
    if answer.get('verdict')!='reachable':raise ValueError('Expected positive witness')
    marking=check(problem,answer['segments'])
    if list(map(int,answer['marking']))!=marking:raise ValueError('Reported marking differs')
    print(json.dumps(dict(status='passed',marking=list(map(str,marking)))))


if __name__=='__main__':main()
