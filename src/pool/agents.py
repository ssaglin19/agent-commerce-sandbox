"""Scripted participant agents. They review terms and speak for their person but cannot approve payments."""
class Agent:
    def __init__(self, name, max_cents): self.name, self.max = name, max_cents
    def review(self, plan):
        share = next(m["share"] for m in plan.members if m["name"] == self.name)
        if share <= self.max:
            return f"Share ${share/100:.2f} is within {self.name}'s ${self.max/100:.2f} limit. Recommending approval. A human still has to approve."
        return f"Share ${share/100:.2f} is above {self.name}'s ${self.max/100:.2f} limit. Recommending no."
